#!/usr/bin/env python3
"""Sync word count / read time on blog/index.html from each post page's own meta.

- EN list stats := post page's EN stats (source of truth: what the post displays).
- If the post has Chinese stats, the list meta becomes bilingual spans
  (lang-en / lang-zh) so the global language toggle switches it.
- If the post has no Chinese version, the meta stays a plain single value
  (the EN span with no zh sibling is shown in zh mode by navbar.html JS).
"""
import re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, 'blog', 'index.html')
SEP = '   \u00b7   '

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def page_stats(path):
    s = open(path, encoding='utf-8').read()
    metas = re.findall(r'<p class="post-meta">(.*?)</p>', s, re.S)
    meta = norm(metas[0]) if metas else ''
    en = re.search(r'([\d,]+)\s*words\s*·\s*(\d+)\s*min read', meta)
    zh = re.search(r'(约\s*)?([\d,]+)\s*字\s*·\s*(\d+)\s*分钟', meta)
    return en, zh

text = open(LIST, encoding='utf-8').read()
href_re = re.compile(r'href="([^"]+)"')
meta_re = re.compile(r'(<p class="post-meta">)(.*?)(</p>)', re.S)
POST_HREF = re.compile(r'^/blog/\d{4}/[^/"]+/?$')

changed = []

def strip_stats(inner):
    """Reduce a list meta inner-HTML to just its trailing date/link remainder.
    Idempotent: unwraps any lang-en span (possibly nested from earlier runs)
    before stripping the leading stats clause."""
    s = norm(inner)
    while True:
        m = re.search(r'<span class="lang-en">(.*?)</span>', s, re.S)
        if not m:
            break
        s = norm(m.group(1))
    s = re.sub(r'^[\d,]+\s+words\s*·\s*', '', s)
    s = re.sub(r'^\d+\s+min read\s*·\s*', '', s)
    return s.strip()

def repl(m):
    open_t, inner, close_t = m.groups()
    prior = list(href_re.finditer(text, 0, m.start()))
    href = prior[-1].group(1) if prior else ''
    if not POST_HREF.match(href):
        return m.group(0)
    path = os.path.join(ROOT, href.strip('/'), 'index.html')
    if not os.path.isfile(path):
        return m.group(0)
    en, zh = page_stats(path)
    if not en:
        return m.group(0)
    remainder = strip_stats(inner)
    en_txt = f'{en.group(1)} words{SEP}{en.group(2)} min read{SEP}{remainder}'
    if zh:
        yue = '约 ' if zh.group(1) else ''
        zh_txt = f'{yue}{zh.group(2)} 字{SEP}{zh.group(3)} 分钟阅读{SEP}{remainder}'
        new_inner = (f'<span class="lang-en"> {en_txt} </span>'
                     f'<span class="lang-zh" style="display:none;"> {zh_txt} </span>')
    else:
        new_inner = f' {en_txt} '
    changed.append(href)
    return f'{open_t}{new_inner}{close_t}'

new_text = meta_re.sub(repl, text)
open(LIST, 'w', encoding='utf-8').write(new_text)
print(f'Updated {len(changed)} entries:')
for h in changed:
    print(' -', h)
