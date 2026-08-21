#!/usr/bin/env python3
"""Fail if a photo credit disagrees with how many people are in the photograph.

Why this exists
---------------
A credit names who is in a frame, and the frame either bears that out or it does
not. This caught a real mistake: a note about "the University of Washington
students I sponsored to attend" was attached to a two-person photograph, while
the actual seven-person group shot sitting next to it had no credit at all. Every
other check passed, because a caption on the wrong picture is still valid HTML
and still bilingual.

The rule is deliberately narrow, so it flags errors rather than opinions:

  * a credit that speaks of a group, a team or students needs three or more
    faces. Two people are not a group.
  * a credit naming two or more people needs at least two faces.
  * a credit naming exactly one other person needs at least one face.

Nothing here objects to a credit naming two people in a crowd of fourteen: that
is normal, and the count only sets a floor. Face detection is also not perfect,
so the floors are lower bounds rather than equality tests.

    python3 scripts/check_photo_credits.py
    python3 scripts/check_photo_credits.py --list

Needs swiftc, for scripts/facecount.swift. Says so and fails rather than
skipping quietly, on the same reasoning as check_photo_masks.py.
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "photos" / "events" / "index.html"
FACECOUNT = ROOT / "scripts" / "facecount.swift"

# A group claim has to be about who is in the frame, not a word that happens to
# appear in someone's job title or in what they were announcing. Two false
# positives made that point: "announcing the new Ambassadors" is about people
# elsewhere in the room, and "Lead of the Cloud Native Open Source Team" is a
# title. Both are checked only after parenthetical titles are stripped.
GROUP_PATTERNS = (
    re.compile(r"\bgroup photo\b", re.I),
    re.compile(r"\bwith the\b[^.]{0,40}?\b(?:group|team)\b", re.I),
    re.compile(r"\bstudents\b", re.I),
    re.compile(r"^the\b[^.]{0,30}\bambassadors\b", re.I),
)
# A credit is a person credit when it opens with "With"; "Photograph by" names
# whoever held the camera, who is by definition not in the frame.
TITLE_TAIL = re.compile(r"\s*\([^)]*\)")


def frames_from_page() -> list[tuple[str, str]]:
    """(largest derivative path, credit text) for every credited frame."""
    text = PAGE.read_text(encoding="utf-8")
    out = []
    for fig in re.findall(r"<figure class=\"figure frame\">(.*?)</figure>", text, re.S):
        credit = re.search(r'class="f-credit"[^>]*>(.*?)</figcaption>', fig, re.S)
        if not credit:
            continue
        full = re.search(r'data-full="([^"]+)"', fig)
        if not full:
            continue
        en = re.search(r'<span class="lang-en">(.*?)</span>', credit.group(1), re.S)
        raw = en.group(1) if en else credit.group(1)
        out.append((full.group(1).lstrip("/"),
                    html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()))
    return out


def required_faces(credit: str) -> tuple[int, str]:
    # Strip parenthetical titles first: they carry words like "Team" and names
    # joined by "and", neither of which says anything about the photograph.
    bare = TITLE_TAIL.sub("", credit)
    if any(pat.search(bare) for pat in GROUP_PATTERNS):
        return 3, "speaks of a group"
    if not bare.startswith("With"):
        return 0, "not a person credit"
    people = len(re.findall(r"\b(?:With|and)\s+[A-Z]", bare))
    return (2, "names two or more people") if people >= 2 else \
           (1, "names one other person")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    frames = frames_from_page()
    if not frames:
        print("no credited frames found", file=sys.stderr)
        return 1
    if not shutil.which("swiftc"):
        print("cannot run: swiftc not found. This gate does not pass by default.",
              file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as td:
        binary = pathlib.Path(td) / "facecount"
        try:
            subprocess.run(["swiftc", "-O", "-o", str(binary), str(FACECOUNT)],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            print(f"cannot build facecount:\n{exc.stderr}", file=sys.stderr)
            return 1
        paths = [str(ROOT / f) for f, _ in frames]
        out = subprocess.run([str(binary), *paths], capture_output=True, text=True)

    faces = {}
    for line in out.stdout.splitlines():
        if "\t" in line:
            name, val = line.split("\t", 1)
            faces[name] = int(val.split("=")[1]) if val.startswith("faces=") else -1

    problems = []
    for rel, credit in frames:
        name = pathlib.Path(rel).name
        n = faces.get(name, -1)
        need, why = required_faces(credit)
        if need and 0 <= n < need:
            problems.append((rel, credit, n, need, why))
        elif args.list:
            print(f"ok    {name:<44} faces={n:<3} needs>={need}  {credit[:44]}")

    print(f"\nphoto credit check: {len(frames)} credited frame(s)")
    for rel, credit, n, need, why in problems:
        print(f"  MISMATCH  {rel}\n"
              f"      faces detected: {n}, expected at least {need} ({why})\n"
              f"      credit: {credit[:90]}\n"
              f"      Is this credit on the right frame?")
    if problems:
        print(f"\nFAIL: {len(problems)} credit(s) do not match their photograph.",
              file=sys.stderr)
        return 1
    print("every credit is consistent with its photograph. clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
