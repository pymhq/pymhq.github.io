#!/usr/bin/env python3
"""Rename photo sources from camera filenames to their published slugs.

Why
---
The sources arrive as IMG_5011.HEIC, Gemini_Generated_Image_7z3s90....jpeg and
52838044610_7da8f11a65_o.jpg. Those names say nothing, two of them collide
conceptually, and one contains spaces. The published derivatives already carry
meaningful slugs, so this gives the originals the same names: IMG_5011.HEIC
becomes 2023-kubecon-eu-f.heic.

Only files outside the repository are touched, which in practice means
~/Pictures/events. Sources that live in the repo keep their names, because other
pages reference them: assets/invited-talks/Onboard.jpg is on the studio page and
assets/blog/lunch-with-mattwhite/lunch-with-matt.png is in a post.

Every rename is written to scripts/photo-source-names.tsv before anything moves,
so the mapping is in version control and the operation can be undone.

    python3 scripts/rename_photo_sources.py            # dry run
    python3 scripts/rename_photo_sources.py --apply    # rename and rewrite paths
    python3 scripts/rename_photo_sources.py --revert   # undo, using the manifest
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from build_photo_derivatives import SOURCES, resolve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "build_photo_derivatives.py"
MANIFEST = ROOT / "scripts" / "photo-source-names.tsv"


def plan() -> list[tuple[str, str, pathlib.Path, pathlib.Path]]:
    """(slug, spec, current, target) for each external source needing a rename."""
    out = []
    for entry in SOURCES:
        spec, slug = entry[0], entry[2]
        if not spec.startswith(("~", "/")):
            continue                      # in-repo asset, referenced elsewhere
        cur = resolve(spec)
        target = cur.with_name(slug + cur.suffix.lower())
        if cur.name != target.name:
            out.append((slug, spec, cur, target))
    return out


def apply(rows) -> int:
    problems = []
    for slug, spec, cur, target in rows:
        if not cur.exists():
            problems.append(f"missing: {cur}")
        if target.exists() and target != cur:
            problems.append(f"target already exists: {target}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    # Merge, never overwrite. A later run only ever has the files that still
    # need renaming, so opening this in write mode drops the provenance of
    # everything renamed earlier. That happened once and cost the mapping for
    # eighty files.
    existing: dict[str, list[str]] = {}
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                existing[row["slug"]] = [row["slug"], row["original_name"],
                                         row["new_name"], row["directory"]]
    for slug, spec, cur, target in rows:
        existing[slug] = [slug, cur.name, target.name, str(cur.parent)]

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["slug", "original_name", "new_name", "directory"])
        for row in sorted(existing.values()):
            w.writerow(row)

    text = BUILD.read_text(encoding="utf-8")
    for slug, spec, cur, target in rows:
        new_spec = spec.replace(cur.name, target.name)
        if spec not in text:
            print(f"cannot find {spec!r} in the build script", file=sys.stderr)
            return 1
        text = text.replace(f'"{spec}"', f'"{new_spec}"')
        cur.rename(target)
    BUILD.write_text(text, encoding="utf-8")
    print(f"renamed {len(rows)} file(s); mapping in "
          f"{MANIFEST.relative_to(ROOT)}")
    return 0


def revert() -> int:
    if not MANIFEST.exists():
        print("no manifest to revert from", file=sys.stderr)
        return 1
    text = BUILD.read_text(encoding="utf-8")
    n = 0
    with MANIFEST.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            d = pathlib.Path(row["directory"])
            new, old = d / row["new_name"], d / row["original_name"]
            if new.exists():
                new.rename(old)
                n += 1
            text = text.replace(row["new_name"], row["original_name"])
    BUILD.write_text(text, encoding="utf-8")
    print(f"reverted {n} file(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        return revert()

    rows = plan()
    if not rows:
        print("nothing to rename; every external source already uses its slug.")
        return 0

    width = max(len(r[2].name) for r in rows)
    for slug, spec, cur, target in rows:
        print(f"  {cur.name:<{width}}  ->  {target.name}")
    print(f"\n{len(rows)} file(s) would be renamed in "
          f"{len({r[2].parent for r in rows})} directory(ies).")
    if not args.apply:
        print("dry run. re-run with --apply to perform the rename.")
        return 0
    return apply(rows)


if __name__ == "__main__":
    sys.exit(main())
