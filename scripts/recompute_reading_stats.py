#!/usr/bin/env python3
"""Recompute accurate EN/ZH word counts + read times for each post page.

EN = shared content + .lang-en blocks/spans -> words @ 200 wpm
ZH = shared content + .lang-zh blocks/spans -> CJK chars + latin words @ 400 cpm

With --fix, rewrites each post page's .post-readstats spans in the first
<p class="post-meta">. Otherwise, reports current vs computed.
"""
import re, os, sys, math, html, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = '--fix' in sys.argv
ONLY = [a for a in sys.argv[1:] if not a.startswith('-')]

def strip_lang(text, cls):
    """Remove balanced <TAG class="...lang-CLS..."> ... </TAG> blocks (div or span)."""
    open_tag = re.compile(r'<(div|span)[^>]*class="[^"]*\blang-%s\b[^"]*"[^>]*>' % cls, re.I)
    out, i = [], 0
    while True:
        m = open_tag.search(text, i)
        if not m:
            out.append(text[i:]); break
        out.append(text[:0] + text[i:m.start()])
        tag = m.group(1).lower()
        token = re.compile(r'<%s\b|</%s>' % (tag, tag), re.I)
        depth, j = 1, m.end()
        for t in token.finditer(text, m.end()):
            if t.group(0).lower().startswith('<' + tag):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    j = t.end(); break
        i = j
    return ''.join(out)

def body_of(s):
    start = 0
    hm = re.search(r'</header>', s, re.I)
    if hm: start = hm.end()
    end = len(s)
    for marker in (r'id="subscribe-placeholder"', r'id="footer-placeholder"', r'<footer\b'):
        em = re.search(marker, s[start:], re.I)
        if em: end = start + em.start(); break
    body = s[start:end]
    body = re.sub(r'<script\b.*?</script>', ' ', body, flags=re.S | re.I)
    body = re.sub(r'<style\b.*?</style>', ' ', body, flags=re.S | re.I)
    body = re.sub(r'<!--.*?-->', ' ', body, flags=re.S)
    return body

def counts(fragment):
    t = re.sub(r'<[^>]+>', ' ', fragment)
    t = html.unescape(t)
    latin = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019/+.-]*", t)
    cjk = re.findall(r'[\u4e00-\u9fff]', t)
    return len(latin), len(cjk)

def fmt(n): return f'{n:,}'

posts = sorted(glob.glob(os.path.join(ROOT, 'blog', '[0-9]*', '*', 'index.html')))
for path in posts:
    rel = '/' + os.path.relpath(os.path.dirname(path), ROOT) + '/'
    if ONLY and not any(o in rel for o in ONLY):
        continue
    s = open(path, encoding='utf-8').read()
    body = body_of(s)
    has_zh = re.search(r'class="[^"]*\blang-zh\b', body)
    en_frag = strip_lang(body, 'zh')
    lat, cjk = counts(en_frag)
    en_words = lat + cjk
    en_min = max(1, math.ceil(en_words / 200))
    zh_words = zh_min = None
    if has_zh:
        zh_frag = strip_lang(body, 'en')
        zlat, zcjk = counts(zh_frag)
        zh_words = zlat + zcjk
        zh_min = max(1, math.ceil(zcjk / 400 + zlat / 200))
    # current meta
    mm = re.search(r'<p class="post-meta">(.*?)</p>', s, re.S)
    meta = re.sub(r'\s+', ' ', mm.group(1)) if mm else ''
    cur_en = re.search(r'([\d,]+)\s*words\s*·\s*(\d+)\s*min read', meta)
    cur_zh = re.search(r'(约\s*)?([\d,]+)\s*字\s*·\s*(\d+)\s*分钟', meta)
    # A page can carry lang-zh in its body while its byline has no Chinese
    # stats at all (blog/2024/productivity). Guarding on has_zh alone then
    # dereferences a None match and kills the whole run on the third post,
    # so the report is gated on the match itself.
    zh_report = (
        f'  ZH: page={(cur_zh.group(2), cur_zh.group(3)) if cur_zh else None}'
        f' computed=({fmt(zh_words)},{zh_min})'
    ) if has_zh else ''
    print(f'{rel:45} EN: page={cur_en.groups() if cur_en else None} computed=({fmt(en_words)},{en_min})'
          + zh_report)
    if FIX and mm:
        new_meta = mm.group(0)
        new_meta = re.sub(r'[\d,]+\s*words\s*·\s*\d+\s*min read',
                          f'{fmt(en_words)} words · {en_min} min read', new_meta)
        if has_zh and cur_zh:
            new_meta = re.sub(r'(约\s*)?[\d,]+\s*字\s*·\s*\d+\s*分钟阅读',
                              f'约 {fmt(zh_words)} 字 · {zh_min} 分钟阅读', new_meta)
        if new_meta != mm.group(0):
            s = s.replace(mm.group(0), new_meta, 1)
            open(path, 'w', encoding='utf-8').write(s)
            print(f'   -> fixed')
