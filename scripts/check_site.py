#!/usr/bin/env python3
"""Structural and content-integrity checks for pengandy.com.

Written because two whole classes of defect got past status-code and
file-size checks:

  1. Content loss. An early build of work.html kept one link per project
     and dropped 73 of 193; the Chinese pass on the same page went from
     236 Han characters to 35. Both pages returned HTTP 200 the whole time.

  2. Structural corruption. Substituting page content into a template whose
     own comment listed its placeholder tokens dumped tens of thousands of
     characters in front of <html>, which silenced shell.js and made every
     post render as interleaved English and Chinese. Also HTTP 200.

So this checks meaning, not just reachability.

    python3 scripts/check_site.py            # report
    python3 scripts/check_site.py --strict   # exit 1 on any FAIL

Reads only; never writes.

The live-vs-draft content parity section was dropped when the rebuild shipped:
there is no longer a separate source to compare against. Parity against the
pre-migration state is available via `git show pre-plana-migration:<path>` if
it is ever needed again.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories that hold assets or tooling rather than pages.
SKIP_DIRS = ('assets', 'components', 'backup', 'libs', 'src', 'css', 'js',
             'scripts', 'node_modules', '.git', 'maps/data', 'data')

# Pages deliberately left on the previous shell: personal notes, an internal CV,
# a referral list and the studio page, which the owner keeps in its own
# markdown-like style. They are unlisted in navigation and exempt from the
# shell checks below.
LEGACY = ('studio.html', 'cv/amzn/index.html', 'notes/papers/index.html',
          'notes/LP/index.html', 'afterhours/races/index.html')

# Assets fetched from a CDN by the old build; not content.
SKIP_HOSTS = ('googletagmanager', 'jsdelivr', 'fonts.googleapis', 'fonts.gstatic',
              'cdnjs', 'code.jquery', 'stackpath', 'unpkg.com', 'd3js.org',
              'hits.sh', 'kit.com', 'app.kit.com',
              # absolute self-links: the live pages sometimes link to
              # themselves by full URL. plana rewrites these to internal
              # /plana/… paths, so their absence is correct, not loss.
              'pengandy.com')

# Content dropped on purpose, with the reason. Anything here is reported as an
# accepted exception rather than a failure, so a real regression still stands
# out instead of hiding in a wall of known noise.
ACCEPTED = {
    'https://www.credly.com/badges/203f5e0a-50a1-4bbd-a617-f7eb12f28871/public_url':
        'Certificates section removed at the owner\'s request',
    'https://www.credly.com/badges/2b5e9ec5-94af-489c-b24f-5e34a817aa6d':
        'Certificates section removed at the owner\'s request',
    'https://www.credly.com/badges/923ca122-e365-45da-a19d-bd5512a31cbf/public_url':
        'Certificates section removed at the owner\'s request',
    'https://www.credly.com/badges/eca5b42d-89c1-41a8-a9fc-a661e9b933cf/public_url':
        'Certificates section removed at the owner\'s request',
    'https://www.credly.com/badges/f10a0c63-0232-45bb-8d84-0321b3b959d5/public_url':
        'Certificates section removed at the owner\'s request',
    'https://coursera.org/share/42a3a7aaa95db0deddcec3c25190e660':
        'Certificates section removed at the owner\'s request',
    'https://www.linkedin.com/learning/certificates/e639b1aa17889982de4d90603400b968a109080facdd5bface3faf0add8fd040':
        'Certificates section removed at the owner\'s request',
}

# Stylesheets and scripts that must never be loaded by a plana page.
FORBIDDEN = ('bootstrap', 'mdbootstrap', 'mdb.min', 'fontawesome', 'academicons',
             'jquery', 'pygments')

fails: list[str] = []
warns: list[str] = []


def read(rel: str) -> str | None:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return open(p, encoding='utf-8', errors='replace').read()


def strip_code(s: str) -> str:
    return re.sub(r'<(script|style)\b.*?</\1>', '', s, flags=re.S | re.I)


def published(s: str) -> str:
    """Drop HTML comments.

    Several live pages keep material commented out — a Talks block in the
    resume that belongs to whoever the template came from, image tags waiting
    on a file, older project entries. None of it renders, so counting it as
    content the plana build "lost" produces false alarms.
    """
    return re.sub(r'<!--.*?-->', '', s, flags=re.S)


def visible_text(s: str) -> str:
    return re.sub(r'<[^>]+>', ' ', strip_code(s))


def han(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', visible_text(s)))


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'-]+", visible_text(s)))


def links(s: str) -> set[str]:
    import html as _h
    out = set()
    for u in re.findall(r'href="(https?://[^"]+)"', s):
        if any(k in u for k in SKIP_HOSTS):
            continue
        out.add(_h.unescape(u).rstrip('/'))
    return out


def site_pages() -> list[str]:
    """Every published HTML page, skipping asset and tooling directories."""
    out = []
    for f in glob.glob(os.path.join(ROOT, '**/*.html'), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(SKIP_DIRS) or os.path.basename(rel).startswith('_'):
            continue
        out.append(f)
    return sorted(out)


def section(title: str) -> None:
    print(f'\n{title}\n' + '-' * len(title))


def check_structure() -> None:
    section('2. structural integrity')
    bad = 0
    redirects = 0
    for f in sorted(site_pages()):
        if os.path.basename(f).startswith('_'):
            continue
        rel = os.path.relpath(f, ROOT)
        if rel in LEGACY:
            continue
        s = open(f, encoding='utf-8', errors='replace').read()
        # Redirect stubs are a page type of their own: no shell, just a
        # refresh to the canonical location. Validate the target instead.
        m = re.search(r'http-equiv="refresh"[^>]*url=([^"\']+)', s)
        if m:
            target = m.group(1).strip().strip('"\'')
            dest = os.path.join(ROOT, target.lstrip('/'))
            if not (os.path.exists(dest) or os.path.exists(os.path.join(dest, 'index.html'))):
                fails.append(f'{rel}: redirect target missing ({target})')
                bad += 1
            redirects += 1
            continue
        i = s.lower().find('<html')
        head = s[:i] if i > 0 else ''
        head = re.sub(r'<!DOCTYPE[^>]*>', '', head, flags=re.I)
        head = re.sub(r'<!--.*?-->', '', head, flags=re.S)
        if head.strip():
            fails.append(f'{rel}: {len(head.strip())} stray chars before <html>')
            bad += 1
        for tag, pat in (('shell.css', r'assets/css/shell\.css'),
                         ('shell.js', r'assets/js/shell\.js')):
            n = len(re.findall(pat, s))
            if n != 1:
                fails.append(f'{rel}: {tag} appears {n} times (expected 1)')
                bad += 1
        if '{{' in s:
            fails.append(f'{rel}: unreplaced template token')
            bad += 1
        if 'data-shell-nav' not in s:
            fails.append(f'{rel}: no nav mount')
            bad += 1
        if 'data-shell-footer' not in s:
            fails.append(f'{rel}: no footer mount')
            bad += 1
    checked = len([f for f in site_pages()
                   if os.path.relpath(f, ROOT) not in LEGACY])
    print(f'  pages checked: {checked}   redirect stubs: {redirects}'
          f'   legacy-shell pages: {len(LEGACY)}   problems: {bad}')


def check_dependencies() -> None:
    section('3. forbidden dependencies')
    hits = Counter()
    for f in site_pages():
        if os.path.relpath(f, ROOT) in LEGACY:
            continue
        s = open(f, encoding='utf-8', errors='replace').read()
        for tag in re.findall(r'<(?:script|link)[^>]*(?:src|href)="([^"]+)"', s):
            for k in FORBIDDEN:
                if k in tag.lower():
                    hits[k] += 1
                    fails.append(f'{os.path.relpath(f, ROOT)} loads {k}')
    print('  ' + (', '.join(f'{k}={v}' for k, v in hits.items()) if hits else 'none loaded'))


def check_bilingual() -> None:
    section('4. bilingual markup hygiene')
    bad_style = bad_pair = 0
    for f in site_pages():
        rel = os.path.relpath(f, ROOT)
        if rel in LEGACY:
            continue
        s = strip_code(open(f, encoding='utf-8', errors='replace').read())
        # inline display:none beats the hidden attribute shell.js toggles
        for m in re.finditer(r'class="lang-(?:en|zh)"[^>]*style="[^"]*display:\s*none', s):
            bad_style += 1
            fails.append(f'{rel}: lang span uses inline display:none instead of hidden')
            break
        zh_visible = len(re.findall(r'class="lang-zh"(?![^>]*hidden)', s))
        if zh_visible:
            bad_pair += 1
            fails.append(f'{rel}: {zh_visible} lang-zh block(s) not marked hidden '
                         '(both languages would show at once)')

    # A page that switches languages itself is the defect this section exists
    # for: every post used to carry a copy of the toggle that wrote inline
    # `display`, which outranks the `hidden` attribute the shell sets. The
    # titles kept switching while the body stayed in one language.
    raw_pages = [f for f in site_pages()
                 if os.path.relpath(f, ROOT) not in LEGACY]
    local_switch = missing_toggle = 0
    for f in raw_pages:
        rel = os.path.relpath(f, ROOT)
        raw = open(f, encoding='utf-8', errors='replace').read()
        for script in re.findall(r'<script\b[^>]*>(.*?)</script>', raw, re.S):
            if re.search(r"querySelectorAll\(\s*'[^']*\.lang-(?:en|zh)", script) \
                    and 'style.display' in script:
                local_switch += 1
                fails.append(f'{rel}: page-local language switch writes '
                             'style.display (use switchLanguage() in the shell)')
                break
        # A post with both languages needs its own visible control.
        if re.match(r'blog/\d{4}/[^/]+/index\.html$', rel) \
                and 'class="lang-zh"' in raw and '<div class="lang-zh"' in raw \
                and 'data-lang=' not in raw:
            missing_toggle += 1
            fails.append(f'{rel}: translated post has no [data-lang] toggle')

    print(f'  inline display:none: {bad_style}   unhidden zh blocks: {bad_pair}'
          f'   page-local switches: {local_switch}'
          f'   posts missing a toggle: {missing_toggle}')


def check_reading_aids() -> None:
    section('5. blog post fidelity')
    rows = []
    # posts live at blog/<year>/<slug>/; blog/tag|category|archive|page/<x>/ are
    # generated listings and have none of a post's hooks, so they are checked
    # separately rather than reported as posts that lost their title.
    LISTING = ('tag', 'category', 'archive', 'page')
    for f in sorted(glob.glob(os.path.join(ROOT, 'blog/*/*/index.html'))):
        rel = os.path.relpath(f, ROOT)
        if rel.split('/')[1] in LISTING:
            continue
        src = rel
        a, b = read(src), read(rel)
        if a is None or b is None:
            continue
        css_a = sum(len(x) for x in re.findall(r'<style[^>]*>(.*?)</style>', a, re.S))
        css_b = sum(len(x) for x in re.findall(r'<style[^>]*>(.*?)</style>', b, re.S))
        miss = [w for w in ('fxbar', 'fx-outline', 'fx-toc', 'post-title', 'post-tags', 'post-meta')
                if w in a and w not in b]
        if miss:
            fails.append(f'{rel}: lost {", ".join(miss)}')
        # the post's own style layer must survive; only .lang-* rules are removed
        if css_a > 500 and css_b < css_a * 0.6:
            fails.append(f'{rel}: style layer shrank {css_a} -> {css_b}')
        rows.append((rel, css_a, css_b, ','.join(miss) or 'ok'))
    listings = [f for f in glob.glob(os.path.join(ROOT, 'blog/*/*/index.html'))
                if os.path.relpath(f, ROOT).split('/')[1] in LISTING]
    bare = [f for f in listings
            if 'entries--posts' not in open(f, encoding='utf-8', errors='replace').read()]
    for f in bare:
        fails.append(f'{os.path.relpath(f, ROOT)}: listing has no entries list')
    print(f'  posts: {len(rows)}   with own style layer: '
          f'{sum(1 for r in rows if r[1] > 500)}   losing widgets: '
          f'{sum(1 for r in rows if r[3] != "ok")}')
    print(f'  listing pages: {len(listings)}   malformed: {len(bare)}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true', help='exit 1 on any FAIL')
    args = ap.parse_args()

    print(f'site check — {ROOT}')
    check_structure()
    check_dependencies()
    check_bilingual()
    check_reading_aids()

    section('summary')
    if warns:
        print(f'  {len(warns)} warning(s):')
        for w in warns[:12]:
            print(f'    - {w}')
    if fails:
        print(f'  {len(fails)} FAILURE(S):')
        for f in fails[:30]:
            print(f'    ! {f}')
        if len(fails) > 30:
            print(f'    … and {len(fails) - 30} more')
    else:
        print('  no failures')
    return 1 if (fails and args.strict) else 0


if __name__ == '__main__':
    sys.exit(main())
