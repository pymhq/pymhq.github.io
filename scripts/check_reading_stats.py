#!/usr/bin/env python3
"""Compare word count / read time between blog/index.html list and each post page (EN + ZH).

The listing keeps its stats in `span.note` inside `span.what`, and drops 阅读
from the Chinese half, so both dialects are parsed leniently here. Reading the
old `p.post-meta` shape, as this did before 2026-08, silently checked nothing
and reported 0 entries while the listing drifted. Run
recompute_reading_stats.py --fix then sync_reading_stats.py to repair.
"""
import re, os, glob, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, 'blog', 'index.html')

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

# ---- 1. Parse list entries ----
src = open(LIST, encoding='utf-8').read()
entries = []  # (href, en_stats, zh_stats, raw_meta)
# Each entry is <a href="/blog/YYYY/slug/"> ... <span class="note">stats</span>
for m in re.finditer(r'href="(/blog/\d{4}/[^"]+/)"[^>]*>.*?<span class="note">(.*?)</span></span>', src, re.S):
    href, meta = m.group(1), norm(m.group(2))
    en = re.search(r'([\d,]+)\s*words\s*·\s*(\d+)\s*min read', meta)
    zh = re.search(r'约?\s*([\d,]+)\s*字\s*·\s*(\d+)\s*分钟', meta)
    entries.append((href, en.groups() if en else None, zh.groups() if zh else None, meta))

# ---- 2. Parse each post page ----
def post_stats(path):
    s = open(path, encoding='utf-8').read()
    metas = re.findall(r'<p class="post-meta">(.*?)</p>', s, re.S)
    meta = norm(metas[0]) if metas else ''
    en = re.search(r'([\d,]+)\s*words\s*·\s*(\d+)\s*min read', meta)
    zh = re.search(r'约?\s*([\d,]+)\s*字\s*·\s*(\d+)\s*分钟', meta)
    return (en.groups() if en else None, zh.groups() if zh else None, meta)

print(f'{"post":48} {"list EN":>16} {"page EN":>16} {"EN?":4} {"list ZH":>16} {"page ZH":>16} {"ZH?":4}')
issues = []
for href, len_, lzh, meta in entries:
    path = os.path.join(ROOT, href.lstrip('/'), 'index.html')
    if not os.path.exists(path):
        print(f'{href:48} (external/no local page)  list={len_}')
        continue
    pen, pzh, pmeta = post_stats(path)
    fmt = lambda t: f'{t[0]}w/{t[1]}m' if t else '-'
    en_ok = 'OK' if len_ == pen else 'X'
    # ZH rule: list zh must equal page zh; if the post has no zh version,
    # the list must have no zh span either (EN span is shown in zh mode).
    zh_ok = 'OK' if (lzh == pzh if pzh else lzh is None and len_ == pen) else 'X'
    print(f'{href:48} {fmt(len_):>16} {fmt(pen):>16} {en_ok:4} {fmt(lzh):>16} {fmt(pzh):>16} {zh_ok:4}')
    if en_ok == 'X' or zh_ok == 'X':
        issues.append(href)
print(f'\n{len(entries)} list entries checked, {len(issues)} with mismatches:')
for i in issues: print(' -', i)
