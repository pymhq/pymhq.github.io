#!/usr/bin/env python3
"""
Add "<N> words   ·   <M> min read" to every local post entry on /blog/index.html.

How it works
------------
* Walks each `<p class="post-meta"> ... </p>` block on blog/index.html.
* Finds the nearest preceding `href="/blog/<year>/<slug>/"` to identify the post.
* Reads that post's index.html, extracts the visible article text (excluding
  <script>/<style> and the hidden `.lang-zh` Chinese mirror so bilingual posts
  are counted once, in English), counts words, and computes reading minutes
  at 200 wpm.
* Rewrites the meta to: "<N> words   ·   <M> min read   ·   <original date/link>",
  preserving the existing trailing date (or year link). Idempotent: re-running
  recomputes rather than stacking.

Run from repo root:  python3 scripts/add_reading_stats.py
"""
from __future__ import annotations

import html
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "blog" / "index.html"
WPM = 200
SEP = "   \u00b7   "  # "   ·   " matches the existing index style

# Matches a single post URL like /blog/2026/speculativedecoding/ (not a year archive).
POST_HREF = re.compile(r"^/blog/\d{4}/[^/\"]+/?$")


def strip_lang_zh(text: str) -> str:
    """Remove balanced <div class="lang-zh"> ... </div> spans (depth-aware)."""
    out = []
    i = 0
    open_tag = re.compile(r'<div[^>]*class="[^"]*\blang-zh\b[^"]*"[^>]*>', re.I)
    div_token = re.compile(r"<div\b|</div>", re.I)
    while True:
        m = open_tag.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        # walk forward from end of the opening tag to find the matching </div>
        depth = 1
        j = m.end()
        for t in div_token.finditer(text, m.end()):
            if t.group(0).lower().startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    j = t.end()
                    break
        i = j  # skip the whole lang-zh block
    return "".join(out)


def count_words(post_html: str) -> int:
    # Content sits between the post <header> and the subscribe/footer block.
    # This covers both templates: new posts keep text inside <article>, older
    # ones use an empty <article> followed by "YOUR CONTENT STARTS HERE".
    start = 0
    hm = re.search(r"</header>", post_html, re.I)
    if hm:
        start = hm.end()
    end = len(post_html)
    for marker in (r'id="subscribe-placeholder"', r'id="footer-placeholder"',
                   r"<footer\b"):
        em = re.search(marker, post_html[start:], re.I)
        if em:
            end = start + em.start()
            break
    body = post_html[start:end]
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)   # HTML comments
    body = strip_lang_zh(body)
    body = re.sub(r"<[^>]+>", " ", body)          # drop tags
    body = html.unescape(body)
    body = re.sub(r"&[a-zA-Z]+;", " ", body)       # leftover entities
    # Latin-ish words + standalone CJK characters (each counts as a word).
    latin = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019/+.-]*", body)
    cjk = re.findall(r"[\u4e00-\u9fff]", body)
    return len(latin) + len(cjk)


def post_file_for(href: str) -> Path | None:
    slug = href.strip("/")  # blog/2026/speculativedecoding
    f = ROOT / slug / "index.html"
    return f if f.is_file() else None


def strip_existing_stats(inner: str) -> str:
    """Remove a leading '<N> words   ·   ' and/or '<M> min read   ·   ' clause."""
    s = inner
    s = re.sub(r"^\s*[\d,]+\s+words\s*\u00b7\s*", "", s)
    s = re.sub(r"^\s*\d+\s+min read\s*\u00b7\s*", "", s)
    return s.strip()


def main() -> int:
    text = INDEX.read_text(encoding="utf-8")
    href_re = re.compile(r'href="([^"]+)"')
    meta_re = re.compile(r'(<p class="post-meta">)(.*?)(</p>)', re.S)

    summary = []
    skipped = []

    def replace(m: re.Match) -> str:
        open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
        # nearest preceding href before this meta block
        prior = list(href_re.finditer(text, 0, m.start()))
        href = prior[-1].group(1) if prior else ""
        if not POST_HREF.match(href):
            skipped.append(href or "(no href)")
            return m.group(0)
        pf = post_file_for(href)
        if not pf:
            skipped.append(href)
            return m.group(0)
        words = count_words(pf.read_text(encoding="utf-8"))
        minutes = max(1, math.ceil(words / WPM))
        remainder = strip_existing_stats(inner)
        new_inner = f" {words:,} words{SEP}{minutes} min read{SEP}{remainder} "
        summary.append((href, words, minutes))
        return f"{open_tag}{new_inner}{close_tag}"

    new_text = meta_re.sub(replace, text)
    INDEX.write_text(new_text, encoding="utf-8")

    print(f"Updated {len(summary)} post entries on {INDEX.relative_to(ROOT)}:\n")
    for href, w, mins in summary:
        print(f"  {w:>6,} words  {mins:>3} min   {href}")
    if skipped:
        uniq = sorted(set(skipped))
        print(f"\nLeft unchanged ({len(uniq)} non-post / external / archive links):")
        for h in uniq:
            print(f"  - {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
