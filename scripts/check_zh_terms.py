#!/usr/bin/env python3
"""Fail on platform names left untranslated in Chinese text.

Why this exists
---------------
ZH-TRANSLATION-SOP.md maps LinkedIn to 领英 and Rednote to 小红书, but the two
places a stale English name hides are easy to miss by eye: a `.lang-zh` label
that was never translated because its English sibling reads fine, and Chinese
prose in a blog body, which is not span-wrapped at all.

A plain grep cannot do this job: every one of these files legitimately contains
`linkedin.com` in an href, `fa-linkedin` in an icon class, and `LinkedIn` in the
English sibling. So this strips tags and attributes first and only inspects text
that a Chinese reader would actually see.

Usage:
    python3 scripts/check_zh_terms.py
    python3 scripts/check_zh_terms.py --files contact.html
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# English term -> required Chinese term.
TERMS = {
    "LinkedIn": "领英",
    "Linkedin": "领英",
    "Rednote": "小红书",
    "Xiaohongshu": "小红书",
    "Google": "谷歌",
}
# Registered organisation and product names: the English word belongs to the
# name itself, so it stays in Chinese copy too, exactly as ZH-TRANSLATION-SOP.md
# already rules for `Amazon Bedrock` and `AWS Lambda`. Checked as a prefix, so
# `Google Cloud` also covers `Google Cloud Run` and `Google Cloud Next`.
EXEMPT_COMPOUNDS = (
    "Google DeepMind", "Google Cloud", "Google X", "Google AI",
    "Google Research", "Google Fonts", "Google I/O", "Google Scholar",
    "Google Meet", "Google Docs", "Google Drive",
)
CJK = re.compile(r"[\u4e00-\u9fff]")
TAG = re.compile(r"<[^>]+>")
DROP_BLOCKS = re.compile(r"<(script|style|svg)\b.*?</\1>", re.S | re.I)
ZH_SPAN = re.compile(r'<span class="lang-zh"[^>]*>(.*?)</span>', re.S)
EN_SPAN = re.compile(r'<span class="lang-en"[^>]*>.*?</span>', re.S)
SKIP_DIRS = {".git", "node_modules"}


def mask(pattern: re.Pattern, src: str) -> str:
    """Blank out matches, keeping newlines so line numbers stay correct.

    The English sibling of a bilingual pair is supposed to say LinkedIn. Without
    this, stripping tags glues "LinkedIn" and "领英" into one string and every
    correctly translated label reports itself as a violation.
    """
    def blank(m: re.Match) -> str:
        return "".join(c if c == "\n" else " " for c in m.group(0))

    return pattern.sub(blank, src)


def text_of(fragment: str) -> str:
    return TAG.sub("", DROP_BLOCKS.sub("", fragment))


def offenders(text: str) -> list[str]:
    """English terms present in text, ignoring registered compound names."""
    found = []
    for en in TERMS:
        for m in re.finditer(re.escape(en), text):
            if any(text.startswith(x, m.start()) for x in EXEMPT_COMPOUNDS):
                continue
            found.append(en)
            break
    return found


def check(path: Path) -> list[tuple[int, str, str]]:
    """Return (line, english term, context) for each untranslated hit."""
    src = path.read_text(encoding="utf-8")
    found: list[tuple[int, str, str]] = []

    # 1. Chinese labels: a lang-zh span that still carries the English name.
    for m in ZH_SPAN.finditer(src):
        inner = text_of(m.group(1))
        for en in offenders(inner):
            line = src[: m.start()].count("\n") + 1
            found.append((line, en, re.sub(r"\s+", " ", inner)[:100]))

    # 2. Chinese prose: any line whose visible text mixes CJK with the English
    #    name. Attributes, hrefs and English siblings are stripped first, so
    #    neither linkedin.com nor a correct EN/ZH pair counts.
    for i, raw in enumerate(mask(EN_SPAN, src).splitlines(), 1):
        visible = text_of(raw)
        if not CJK.search(visible):
            continue
        for en in offenders(visible):
            if any(f[0] == i and f[1] == en for f in found):
                continue
            found.append((i, en, re.sub(r"\s+", " ", visible.strip())[:100]))

    return found


def main() -> int:
    args = sys.argv[1:]
    if "--files" in args:
        paths = [REPO_ROOT / p for p in args[args.index("--files") + 1:]]
    else:
        paths = [
            p for p in REPO_ROOT.rglob("*")
            if p.suffix in {".html", ".xml"}
            and not any(part in SKIP_DIRS for part in p.parts)
        ]

    total = 0
    for path in sorted(paths):
        hits = check(path)
        if not hits:
            continue
        rel = path.relative_to(REPO_ROOT)
        for line, en, ctx in hits:
            print(f"{rel}:{line}: {en} should be {TERMS[en]}")
            print(f"    {ctx}")
            total += 1

    print(f"\nzh term check: {len(paths)} files scanned")
    if total:
        print(f"FAIL: {total} untranslated platform name(s). See ZH-TRANSLATION-SOP.md.")
        return 1
    print("all platform names translated in Chinese text. clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
