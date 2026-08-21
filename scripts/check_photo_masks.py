#!/usr/bin/env python3
"""Fail if any built photo derivative still carries a readable code.

Why this exists
---------------
scripts/build_photo_derivatives.py can blank a region, but a mask box is only
correct in the space the mask is applied in, and that space is not the file on
disk: sips hands Pillow a HEIC as a PNG that still carries its EXIF orientation,
so Pillow rotates it afterwards. A box measured on the unrotated file therefore
lands somewhere else. That is not hypothetical. It happened to a CVPR badge, the
block missed the QR completely, and the published derivative still decoded to 88
bytes of registration data. Every other check in this repo passed while that was
true, because a photograph with a readable barcode in it is a perfectly valid
photograph.

So this checks the output rather than the intent: it runs the same detector over
the files that actually ship, and any symbol at all is a failure. Adding a new
badge photo without a mask fails here, which is the point.

    python3 scripts/check_photo_masks.py
    python3 scripts/check_photo_masks.py --list   # show every file scanned

Needs swiftc for scripts/qrfind.swift. On a machine without it the check cannot
run; it says so and exits non-zero rather than passing silently, since a
privacy gate that quietly skips is worse than none.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "photos"
QRFIND = ROOT / "scripts" / "qrfind.swift"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="print every file scanned")
    args = ap.parse_args()

    files = sorted(ASSETS.rglob("*.webp"))
    if not files:
        print("no derivatives found; run build_photo_derivatives.py first",
              file=sys.stderr)
        return 1

    if not shutil.which("swiftc"):
        print("cannot run: swiftc not found, so scripts/qrfind.swift cannot be "
              "built. This gate does not pass by default.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as td:
        binary = pathlib.Path(td) / "qrfind"
        try:
            subprocess.run(["swiftc", "-O", "-o", str(binary), str(QRFIND)],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            print(f"cannot build qrfind:\n{exc.stderr}", file=sys.stderr)
            return 1

        out = subprocess.run([str(binary), *map(str, files)],
                             capture_output=True, text=True)

    hits, unreadable = [], []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        path, state = parts[0], parts[1]
        rel = pathlib.Path(path).relative_to(ROOT)
        if state == "clean":
            if args.list:
                print(f"clean  {rel}")
        elif state == "unreadable":
            unreadable.append(rel)
        else:
            hits.append((rel, parts[1], parts[2] if len(parts) > 2 else "",
                         parts[3] if len(parts) > 3 else ""))

    print(f"\nphoto mask check: {len(files)} derivative(s) scanned")
    for rel in unreadable:
        print(f"  UNREADABLE {rel}")
    for rel, sym, box, payload in hits:
        print(f"  READABLE CODE  {rel}\n"
              f"      {sym}  box={box}  {payload}\n"
              f"      Measure the mask with scripts/find_photo_masks.py and add "
              f"it to SOURCES.")

    if hits or unreadable:
        print(f"\nFAIL: {len(hits)} readable code(s), "
              f"{len(unreadable)} unreadable file(s).", file=sys.stderr)
        return 1
    print("no readable codes in any published frame. clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
