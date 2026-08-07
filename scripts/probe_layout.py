#!/usr/bin/env python3
"""Measure the reading column of every blog post, in a real browser.

Why this exists
---------------
Typography bugs are invisible to every other check in this repo. During the
2026-08 rebuild the opening paragraph of six posts sat 100px to the left of
the body, and three more posts rendered their entire body 200px too wide.
Every one of those pages returned HTTP 200, contained all its content,
passed check_site.py, and looked plausible in a screenshot. The offset was
exactly (880 - 680) / 2 — the intro lived two levels deeper in the DOM than
the prose-column selectors reached, so it kept the outer container width.

Reading CSS could not have found it: the posts carry 22 different style
layers of their own. Screenshots did not find it either. Measuring the
rendered geometry did, in one pass over all 29 posts.

How it works
------------
Writes a temporary harness page into the repo root, loads each post into an
iframe, and reports for every prose paragraph its left edge and width. Then:

  * the most common left edge is treated as the page's reading column
  * a first paragraph more than TOL px away from it is reported as an
    offset opening — the specific defect that started this
  * pages whose column differs from the rest of the site are reported

Insets are not automatically failures. A paragraph inside a pull-quote,
callout or card is *meant* to be indented, and the tool prints the DOM path
so that judgement can be made from evidence. Use --paths to see them.

Usage
-----
    python3 scripts/probe_layout.py                 # all posts
    python3 scripts/probe_layout.py --paths         # show DOM paths too
    python3 scripts/probe_layout.py --strict        # exit 1 on an offset opening
    python3 scripts/probe_layout.py /blog/2026/decade/ /creativity

Requires Google Chrome and a local server; starts scripts/serve.py if the
port is free. Reads only, apart from a harness file it removes afterwards.
"""

from __future__ import annotations

import argparse
import glob
import html as html_mod
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 8127
TOL = 12          # px: below this, a difference is rounding, not misalignment
MIN_CHARS = 40    # ignore captions, bylines and other short lines

HARNESS = """<!DOCTYPE html><meta charset="utf-8">
<style>body{font:11px/1.5 monospace;margin:0}
iframe{width:1300px;height:900px;border:0;position:absolute;left:-4000px}</style>
<pre id="out">measuring…</pre>
<script>
const pages = __PAGES__, TOL = __TOL__, MIN = __MIN__;
const out = document.getElementById('out'), lines = [];
function path(el, stop) {
  const p = []; let n = el;
  while (n && n !== stop) {
    let s = n.tagName.toLowerCase();
    if (n.id) s += '#' + n.id;
    else if (typeof n.className === 'string' && n.className.trim())
      s += '.' + n.className.trim().split(/\\s+/).slice(0, 2).join('.');
    p.unshift(s); n = n.parentElement;
  }
  return p.join(' > ');
}
(async () => {
  for (const url of pages) {
    const fr = document.createElement('iframe');
    fr.src = url; document.body.appendChild(fr);
    await new Promise(r => { fr.onload = r; setTimeout(r, 4000); });
    try {
      const d = fr.contentDocument, w = fr.contentWindow;
      const root = d.querySelector('.post') || d.querySelector('main');
      if (!root) { lines.push(JSON.stringify({url, error: 'no .post or main'})); fr.remove(); continue; }
      // Every block element, not just <p>. Measuring paragraphs alone missed
      // bare <li> with no list parent, and callout boxes that kept the outer
      // measure while the prose around them was narrower.
      const SEL = 'p,h1,h2,h3,h4,ul,ol,li,img,figure,table,blockquote,pre,div';
      const ps = [...root.querySelectorAll(SEL)].filter(el => {
        const cs = w.getComputedStyle(el);
        if (cs.display === 'none' || el.hidden || el.closest('[hidden]')) return false;
        if (el.closest('.post-meta,.post-tags,.post-views,.fx-toc,#fx-outline,.foot,.nav')) return false;
        const r = el.getBoundingClientRect();
        if (r.width < 20 || r.height < 4) return false;
        // a text block must carry real text; media and containers need not
        if (/^(P|H1|H2|H3|H4|LI|BLOCKQUOTE)$/.test(el.tagName))
          return (el.textContent || '').trim().length >= MIN;
        return true;
      });
      const geo = ps.map(el => {
        const r = el.getBoundingClientRect();
        const bare = el.tagName === 'LI' &&
                     !['UL', 'OL'].includes(el.parentElement.tagName);
        return { l: Math.round(r.left), w: Math.round(r.width), tag: el.tagName.toLowerCase(),
                 bare: bare, path: path(el, root),
                 text: (el.textContent || '').trim().slice(0, 70) };
      });
      // The column is taken from prose that sits directly in a content
      // wrapper. Using the most frequent left edge of *everything* made two
      // posts look misaligned when in fact their callout component simply
      // appeared more often than their paragraphs.
      const WRAP = /(?:^|> )(?:div#markdown-content|div\.lang-en|div\.lang-zh|article\.post-content) > (?:p|h2|h3|li|ul)$/;
      const prose = geo.filter(g => /^(p|h2|h3|li|ul)$/.test(g.tag) &&
                                    (WRAP.test(g.path) || !g.path.includes(' > ')));
      const basis = prose.length ? prose : geo;
      const cnt = {}; basis.forEach(g => cnt[g.l] = (cnt[g.l] || 0) + 1);
      const col = Number(Object.entries(cnt).sort((a, b) => b[1] - a[1])[0]?.[0] || 0);
      // an element wider than the column by more than a rounding margin has
      // escaped the reading measure
      const wcnt = {}; basis.forEach(g => wcnt[g.w] = (wcnt[g.w] || 0) + 1);
      const colw = Number(Object.entries(wcnt).sort((a, b) => b[1] - a[1])[0]?.[0] || 0);
      lines.push(JSON.stringify({ url, n: geo.length, col, colw,
        first: (prose[0] || geo.find(g => /^(p|h2|h3|li)$/.test(g.tag)) || geo[0] || null),
        bare: geo.filter(g => g.bare).length,
        wide: geo.filter(g => g.w > colw + TOL && g.tag !== 'img' && g.tag !== 'figure')
                .map(g => ({ tag: g.tag, l: g.l, w: g.w, path: g.path })),
        insets: geo.filter(g => Math.abs(g.l - col) > TOL) }));
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="*", help="URLs to probe (default: every post)")
    ap.add_argument("--paths", action="store_true", help="print the DOM path of each inset")
    ap.add_argument("--strict", action="store_true", help="exit 1 on an offset opening")
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

    harness = os.path.join(ROOT, "_probe_layout.html")
    open(harness, "w", encoding="utf-8").write(
        HARNESS.replace("__PAGES__", json.dumps(pages))
               .replace("__TOL__", str(TOL)).replace("__MIN__", str(MIN_CHARS)))
    try:
        budget = 8000 * max(len(pages), 1) + 20000
        dom = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--window-size=1400,900",
             f"--virtual-time-budget={budget}", "--dump-dom",
             f"http://localhost:{PORT}/_probe_layout.html"],
            capture_output=True, text=True, timeout=budget / 1000 + 120).stdout
    finally:
        os.remove(harness)
        if server:
            server.terminate()

    m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    if not m:
        print("no measurement returned; is the server up?", file=sys.stderr)
        return 2
    raw = html_mod.unescape(m.group(1))
    if "__DONE__" not in raw:
        print("warning: probe did not finish; results may be partial", file=sys.stderr)

    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    measured = [r for r in rows if not r.get("error") and r.get("n")]
    cols = {}
    for r in measured:
        cols[r["col"]] = cols.get(r["col"], 0) + 1
    site_col = max(cols, key=cols.get) if cols else 0

    print(f"{'page':<40}{'col':>6}{'width':>7}{'open':>6}{'wide':>6}{'bareLi':>7}{'blocks':>8}")
    offsets, odd, wides = [], [], []
    for r in rows:
        if r.get("error"):
            print(f"  {r['url']:<42} ERROR {r['error']}")
            continue
        if not r.get("n"):
            print(f"  {r['url']:<42}  (no prose over {MIN_CHARS} chars)")
            continue
        off = r["first"]["l"] - r["col"] if r["first"] else 0
        note = ""
        if abs(off) > TOL:
            offsets.append(r); note = "  << opening offset"
        if r["col"] != site_col:
            odd.append(r); note += "  << column differs"
        if r.get("wide"):
            wides.append(r); note += f"  << {len(r['wide'])} wider than the column"
        print(f"  {r['url']:<40}{r['col']:>6}{r.get('colw', 0):>7}{off:>6}"
              f"{len(r.get('wide', [])):>6}{r.get('bare', 0):>7}{r['n']:>8}{note}")

    print(f"\n  site reading column: {site_col}px from the viewport edge")
    print(f"  pages measured: {len(measured)}   sharing that column: "
          f"{sum(1 for r in measured if r['col'] == site_col)}")

    if offsets:
        print(f"\n  {len(offsets)} page(s) whose first paragraph is offset — check whether each is an\n"
              f"  intentional epigraph or a real misalignment:")
        for r in offsets:
            print(f"    {r['url']}  off by {r['first']['l'] - r['col']}px")
            print(f"      path: {r['first']['path']}")
            print(f"      text: {r['first']['text']}")

    if wides:
        print(f"\n  {len(wides)} page(s) with a block wider than the reading column:")
        for r in wides:
            for g in r["wide"][:4]:
                print(f"    {r['url']:<38} {g['tag']:<6} w{g['w']}  {g['path']}")

    if args.paths:
        print("\n  insets by DOM path (deliberate component padding shows up here):")
        for r in measured:
            seen = set()
            for g in r["insets"]:
                if g["path"] in seen:
                    continue
                seen.add(g["path"])
                print(f"    {r['url']:<40} {g['l'] - r['col']:+5}px  {g['path']}")

    return 1 if (args.strict and offsets) else 0


if __name__ == "__main__":
    sys.exit(main())
