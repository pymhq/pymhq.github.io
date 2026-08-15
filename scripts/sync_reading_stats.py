#!/usr/bin/env python3
"""Sync word count / read time on blog/index.html from each post page.

Source of truth is what the post itself displays, so run
recompute_reading_stats.py --fix first, then this.

Why this was rewritten
----------------------
The original targeted `<p class="post-meta">` in the listing and wrote the
Chinese half as `style="display:none;"`. Neither survives today's markup: the
2026-08 rebuild moved listing stats into `span.note` inside `span.what`, so the
script matched nothing and reported "Updated 0 entries" on every run while the
listing quietly drifted, and inline display:none is now a failure in
check_site.py's bilingual hygiene pass, which requires the `hidden` attribute.

Note the two dialects, which are deliberate and preserved here:
    post page:  · 2,803 words · 15 min read   /   · 约 4,873 字 · 15 分钟阅读
    listing:      2,803 words · 15 min read · research · products
                  约 4,873 字 · 15 分钟 · research · products
The listing appends the post's categories and drops 阅读, so this rewrites only
the stats clause and carries the remainder through untouched.

Usage:
    python3 scripts/sync_reading_stats.py            # write
    python3 scripts/sync_reading_stats.py --dry-run  # report only
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIST = REPO_ROOT / "blog" / "index.html"
SEP = " \u00b7 "

POST_HREF = re.compile(r'href="(/blog/\d{4}/[^"]+/)"')
META = re.compile(r'<p class="post-meta">(.*?)</p>', re.S)
EN_STATS = re.compile(r"([\d,]+)\s*words\s*\u00b7\s*(\d+)\s*min read")
ZH_STATS = re.compile(r"(\u7ea6\s*)?([\d,]+)\s*\u5b57\s*\u00b7\s*(\d+)\s*\u5206\u949f")
# The stats clause at the head of a listing note, with the remainder after it.
EN_NOTE = re.compile(r"^\s*[\d,]+\s*words\s*\u00b7\s*\d+\s*min read\s*(?:\u00b7\s*)?")
ZH_NOTE = re.compile(r"^\s*(?:\u7ea6\s*)?[\d,]+\s*\u5b57\s*\u00b7\s*\d+\s*\u5206\u949f\s*(?:\u00b7\s*)?")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def span_end(src: str, open_end: int) -> int:
    """Index just past the </span> matching a span that opened before open_end.

    The note span contains lang-en / lang-zh children, so a non-greedy
    .*?</span> would stop at the first child's close tag.
    """
    depth, i = 1, open_end
    token = re.compile(r"<span\b|</span>", re.I)
    while depth:
        m = token.search(src, i)
        if not m:
            return -1
        depth += 1 if m.group(0).lower().startswith("<span") else -1
        i = m.end()
    return i


def page_stats(path: Path):
    """(en_words, en_min), (yue, zh_words, zh_min) as displayed by the post."""
    if not path.is_file():
        return None, None
    m = META.search(path.read_text(encoding="utf-8"))
    if not m:
        return None, None
    meta = norm(m.group(1))
    return EN_STATS.search(meta), ZH_STATS.search(meta)


def main() -> int:
    dry = "--dry-run" in sys.argv
    src = LIST.read_text(encoding="utf-8")
    out, cursor, changed, skipped = [], 0, [], []

    for href_m in POST_HREF.finditer(src):
        href = href_m.group(1)
        note_m = re.compile(r'<span class="note">').search(src, href_m.end())
        if not note_m:
            continue
        inner_end = span_end(src, note_m.end())
        if inner_end < 0:
            continue
        inner = src[note_m.end(): inner_end - len("</span>")]

        en, zh = page_stats(REPO_ROOT / href.strip("/") / "index.html")
        if not en:
            skipped.append(href)
            continue

        # Keep whatever trails the stats clause (categories) exactly as found.
        en_old = re.search(r'<span class="lang-en">(.*?)</span>', inner, re.S)
        zh_old = re.search(r'<span class="lang-zh"[^>]*>(.*?)</span>', inner, re.S)
        en_rest = EN_NOTE.sub("", norm(en_old.group(1))) if en_old else ""
        zh_rest = ZH_NOTE.sub("", norm(zh_old.group(1))) if zh_old else en_rest

        en_txt = f"{en.group(1)} words{SEP}{en.group(2)} min read"
        if en_rest:
            en_txt += SEP + en_rest

        if zh:
            yue = "\u7ea6 " if zh.group(1) else ""
            zh_txt = f"{yue}{zh.group(2)} \u5b57{SEP}{zh.group(3)} \u5206\u949f"
            if zh_rest:
                zh_txt += SEP + zh_rest
            new_inner = (f'<span class="lang-en">{en_txt}</span>'
                         f'<span class="lang-zh" hidden>{zh_txt}</span>')
        elif zh_old:
            # Post lost its Chinese stats: leave the listing's Chinese line be
            # rather than silently deleting a translation.
            new_inner = f'<span class="lang-en">{en_txt}</span>' + zh_old.group(0)
        else:
            new_inner = f'<span class="lang-en">{en_txt}</span>'

        if norm(new_inner) != norm(inner):
            changed.append((href, norm(inner)[:70], norm(new_inner)[:70]))
        out.append(src[cursor:note_m.end()])
        out.append(new_inner)
        cursor = inner_end - len("</span>")

    out.append(src[cursor:])
    new_src = "".join(out)

    print(f"{len(changed)} listing entr{'y' if len(changed) == 1 else 'ies'} out of sync")
    for href, before, after in changed:
        print(f"  {href}\n    was: {before}\n    now: {after}")
    if skipped:
        print(f"no stats on page, left alone: {', '.join(skipped)}")

    if dry:
        print("\ndry run, nothing written")
    elif changed:
        LIST.write_text(new_src, encoding="utf-8")
        print("\nblog/index.html updated")
    else:
        print("\nalready in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
