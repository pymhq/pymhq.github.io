#!/usr/bin/env python3
"""Fail on em dashes in lines you are adding.

Why this exists
---------------
WRITING-SOP.md bans the em dash in new content, but the site already carries
about 3,300 of them across 118 files. A whole-file grep is therefore useless as
a gate: it is red on every page, so it gets ignored. This reads the diff instead
and only inspects ADDED lines, which is exactly the scope of the rule.

Four spellings count as violations: the literal U+2014, the HTML entity
&mdash;, its numeric forms &#8212; / &#x2014;, and the Chinese doubled ——
(two U+2014, caught by the same check).

The en dash U+2013 is legal between numbers or dates (2023-2026, pp. 14-18) and
illegal in prose, so it is reported as a warning with the line for a human to
judge, never as a failure.

Two escape hatches, both narrow:

  * The files that DEFINE the rule (WRITING-SOP.md and this script) have to
    spell the banned characters out, so they are skipped wholesale.
  * Any single line containing the token `dash-ok` is exempt. Use it only when
    quoting someone else's text verbatim, where silently repunctuating them
    would be a misquote.

Usage:
    python3 scripts/check_dashes.py                  # staged + unstaged vs HEAD
    python3 scripts/check_dashes.py --staged         # staged only
    python3 scripts/check_dashes.py --files a.html   # whole-file scan
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EM = "\u2014"
EN = "\u2013"
ENTITY = re.compile(r"&mdash;|&#8212;|&#x2014;", re.I)
# A dash between digits, or between years/dates, is a range: legal.
RANGE_EN = re.compile(r"(?<=\d)%s(?=\d)" % EN)
TEXT_SUFFIXES = {".html", ".md", ".xml", ".txt", ".json", ".py", ".css", ".js"}
# The rule's own definition has to quote the characters it bans.
SELF_EXEMPT = {"WRITING-SOP.md", "scripts/check_dashes.py"}
LINE_EXEMPT = "dash-ok"


def diff_added_lines(staged_only: bool) -> list[tuple[str, int, str]]:
    """Return (path, line number in new file, text) for every added line."""
    cmd = ["git", "diff", "--unified=0", "--no-color"]
    if staged_only:
        cmd.append("--cached")
    cmd.append("HEAD")
    out = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True).stdout

    added: list[tuple[str, int, str]] = []
    path, lineno = None, 0
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@"):
            # @@ -old,count +new,count @@
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            if path:
                added.append((path, lineno, line[1:]))
            lineno += 1
    return added


def whole_file_lines(paths: list[str]) -> list[tuple[str, int, str]]:
    rows = []
    for p in paths:
        fp = REPO_ROOT / p
        if not fp.is_file():
            print(f"skip (not a file): {p}")
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # An untracked image or font is not prose. Before this, one new
            # binary in the working tree crashed the gate the SOP tells you
            # to run before committing.
            continue
        for i, line in enumerate(text.splitlines(), 1):
            rows.append((p, i, line))
    return rows


def untracked_lines() -> list[tuple[str, int, str]]:
    """Every line of a new, not-yet-tracked file counts as added.

    git diff HEAD does not see untracked files, so without this a brand new
    post or SOP would pass the gate by being invisible to it.
    """
    out = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout
    return whole_file_lines([p for p in out.splitlines() if p])


def main() -> int:
    args = sys.argv[1:]
    if "--files" in args:
        rows = whole_file_lines(args[args.index("--files") + 1:])
        scope = "whole file"
    else:
        staged = "--staged" in args
        rows = diff_added_lines(staged_only=staged) + untracked_lines()
        scope = "staged diff + untracked" if staged else "diff vs HEAD + untracked"

    fails, warns = [], []
    for path, lineno, text in rows:
        if Path(path).suffix not in TEXT_SUFFIXES:
            continue
        if path in SELF_EXEMPT or LINE_EXEMPT in text:
            continue
        if EM in text or ENTITY.search(text):
            fails.append((path, lineno, text))
        elif EN in text and not RANGE_EN.search(text):
            warns.append((path, lineno, text))

    print(f"em dash check ({scope}): {len(rows)} lines inspected")

    if warns:
        print(f"\nen dash outside a numeric range ({len(warns)}), check by eye:")
        for path, lineno, text in warns:
            print(f"  {path}:{lineno}: {text.strip()[:120]}")

    if fails:
        print(f"\nFAIL: em dash in {len(fails)} added line(s). See WRITING-SOP.md.")
        for path, lineno, text in fails:
            print(f"  {path}:{lineno}: {text.strip()[:120]}")
        return 1

    print("\nno em dashes added. clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
