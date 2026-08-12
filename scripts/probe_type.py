#!/usr/bin/env python3
"""Measure the computed type size of shared post components, in a real browser.

Why this exists
---------------
The posts carry their own style layers, so the same component can be defined
twice with different numbers — a 2026 comment note is .93rem on one post and
0.88em on another, and nothing in the repo notices. font-size also can't be
compared by reading CSS alone: em is relative to its parent and rem to the
root, so two different declarations can agree and two identical ones can
disagree. Only the computed value in a browser settles it.

How it works
------------
Loads every post into an iframe (same trick as probe_layout.py) and reports
getComputedStyle().fontSize for one element per component per page. Runs the
sweep twice, once in English and once with ?lang=zh, because a language
switch must not change the size of anything.

A component is reported as inconsistent when it renders at more than one
size across the posts that use it.

Usage
-----
    python3 scripts/probe_type.py            # every post, EN + ZH
    python3 scripts/probe_type.py --en       # English only
    python3 scripts/probe_type.py --strict   # exit 1 if a component disagrees

Requires Google Chrome and a local server; starts scripts/serve.py if the
port is free. Read-only, apart from a harness file it removes afterwards.
"""

from __future__ import annotations

import argparse
import glob
import html as html_mod
import json
import os
import re
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 8128

# component -> CSS selector. Keep to components that appear on more than one
# post; single-use decoration is a style choice, not a consistency bug.
COMPONENTS = {
    "prose p":          ".post-content p, #markdown-content p",
    "prose li":         ".post-content ul > li, #markdown-content ul > li",
    "note 2026":        ".comment-note-2026",
    "note 2026 date":   ".comment-note-2026 .note-date",
    "note 2025":        ".comment-note-2025",
    "note 2025 date":   ".comment-note-2025 .note-date",
    "note sublist li":  ".comment-note-2026 .note-sublist > li, .comment-note-2025 .note-sublist > li",
    "tl sublist li":    ".timeline-description .note-sublist > li",
    "timeline date":    ".timeline-date",
    "timeline body":    ".timeline-description",
}

HARNESS = """<!DOCTYPE html><meta charset="utf-8">
<style>body{font:11px/1.5 monospace;margin:0}
iframe{width:1300px;height:900px;border:0;position:absolute;left:-4000px}</style>
<pre id="out">measuring…</pre>
<script>
const pages = __PAGES__, comps = __COMPS__;
const out = document.getElementById('out'), lines = [];
(async () => {
  for (const url of pages) {
    const fr = document.createElement('iframe');
    fr.src = url; document.body.appendChild(fr);
    await new Promise(r => { fr.onload = r; setTimeout(r, 3000); });
    try {
      const d = fr.contentDocument, w = fr.contentWindow;
      const found = {};
      for (const [name, sel] of Object.entries(comps)) {
        // Every match that carries text, reduced to its most common size.
        // Taking the first match instead reported six posts as inconsistent
        // body text when what it had actually measured was their opening
        // lede paragraph, which is meant to be larger.
        // A hidden element still reports the size it would render at, which
        // is what the ZH pass needs.
        const els = [...d.querySelectorAll(sel)]
          .filter(e => (e.textContent || '').trim().length > 8);
        if (!els.length) continue;
        const tally = {};
        let cs0 = null;
        for (const el of els) {
          const cs = w.getComputedStyle(el);
          const px = parseFloat(cs.fontSize).toFixed(2);
          tally[px] = (tally[px] || 0) + 1;
          if (!cs0) cs0 = cs;
        }
        const top = Object.entries(tally).sort((a, b) => b[1] - a[1])[0];
        found[name] = { size: top[0], n: els.length, spread: Object.keys(tally).length,
                        lh: cs0.lineHeight,
                        fam: (cs0.fontFamily || '').split(',')[0].replace(/["']/g, '') };
      }
      lines.push(JSON.stringify({ url, found }));
    } catch (e) { lines.push(JSON.stringify({ url, error: e.message })); }
    fr.remove(); out.textContent = lines.join('\\n');
  }
  out.textContent = lines.join('\\n') + '\\n__DONE__';
})();
</script>
"""


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def posts() -> list[str]:
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "blog/*/*/index.html"))):
        rel = os.path.relpath(f, ROOT)
        if rel.split("/")[1] in ("tag", "category", "archive", "page"):
            continue
        out.append("/" + os.path.dirname(rel) + "/")
    return out


def measure(pages: list[str], suffix: str) -> list[dict]:
    urls = [p + suffix for p in pages]
    harness = os.path.join(ROOT, "_probe_type.html")
    open(harness, "w", encoding="utf-8").write(
        HARNESS.replace("__PAGES__", json.dumps(urls))
               .replace("__COMPS__", json.dumps(COMPONENTS)))
    try:
        budget = 6000 * max(len(urls), 1) + 20000
        dom = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--window-size=1400,900",
             f"--virtual-time-budget={budget}", "--dump-dom",
             f"http://localhost:{PORT}/_probe_type.html"],
            capture_output=True, text=True, timeout=budget / 1000 + 120).stdout
    finally:
        os.remove(harness)

    m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    if not m:
        return []
    raw = html_mod.unescape(m.group(1))
    if "__DONE__" not in raw:
        print("warning: probe did not finish; results may be partial", file=sys.stderr)
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def report(rows: list[dict], label: str) -> int:
    by_comp: dict[str, dict[str, list[str]]] = {}
    for r in rows:
        if r.get("error"):
            print(f"  ERROR {r['url']}: {r['error']}")
            continue
        for name, v in r.get("found", {}).items():
            by_comp.setdefault(name, {}).setdefault(v["size"], []).append(r["url"])

    print(f"\n{label}")
    print("-" * len(label))
    bad = 0
    for name in COMPONENTS:
        sizes = by_comp.get(name)
        if not sizes:
            continue
        pages = sum(len(v) for v in sizes.values())
        if len(sizes) == 1:
            size = next(iter(sizes))
            print(f"  {name:<18} {size + 'px':>9}   consistent across {pages} page(s)")
        else:
            bad += 1
            print(f"  {name:<18} {'MIXED':>9}   {len(sizes)} sizes across {pages} page(s)")
            for size, urls in sorted(sizes.items(), key=lambda kv: -len(kv[1])):
                for u in sorted(urls):
                    print(f"      {size + 'px':>9}   {u}")
    print(f"\n  components measured: {len([c for c in COMPONENTS if c in by_comp])}"
          f"   inconsistent: {bad}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="*")
    ap.add_argument("--en", action="store_true", help="English pass only")
    ap.add_argument("--strict", action="store_true", help="exit 1 if a component disagrees")
    args = ap.parse_args()

    if not os.path.exists(CHROME):
        print(f"Chrome not found at {CHROME}", file=sys.stderr)
        return 2

    pages = args.pages or posts()
    server = None
    if not port_open(PORT):
        server = subprocess.Popen([sys.executable, os.path.join(ROOT, "scripts/serve.py"), str(PORT)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    try:
        bad = report(measure(pages, ""), f"English · {len(pages)} pages")
        if not args.en:
            bad += report(measure(pages, "?lang=zh"), f"中文 · {len(pages)} pages")
    finally:
        if server:
            server.terminate()

    print()
    return 1 if (args.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
