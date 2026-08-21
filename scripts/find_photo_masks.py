#!/usr/bin/env python3
"""Find machine-readable codes in photo sources and print paste-ready masks.

Why this exists
---------------
A mask box is only correct in the space the mask is applied in, and that space
is not the file on disk. sips hands Pillow a HEIC as a PNG that still carries
its EXIF orientation, so Pillow rotates it, and a box measured on the unrotated
file lands in the wrong place. That happened once: the block missed a CVPR badge
QR entirely and the code stayed readable in the published derivative, which is
the exact thing the mask existed to prevent.

So this renders each source through the same code path the build uses, then runs
the detector on that, and prints the tuple to paste into SOURCES. There is no
step where a human converts coordinates by hand.

    python3 scripts/find_photo_masks.py ~/Pictures/events/IMG_1106.HEIC
    python3 scripts/find_photo_masks.py --all      # every source in SOURCES

Requires swiftc, for scripts/qrfind.swift. macOS only, like the HEIC path.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from build_photo_derivatives import (  # noqa: E402
    SOURCES, ROOT, open_frame, resolve,
)

try:
    from PIL import ImageOps
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required")

QRFIND = pathlib.Path(__file__).resolve().parent / "qrfind.swift"


def build_detector(tmp: pathlib.Path) -> pathlib.Path:
    if not shutil.which("swiftc"):
        sys.exit("swiftc not found; this tool needs the macOS toolchain")
    out = tmp / "qrfind"
    subprocess.run(["swiftc", "-O", "-o", str(out), str(QRFIND)],
                   check=True, capture_output=True)
    return out


def masking_space(src: pathlib.Path, tmp: pathlib.Path) -> pathlib.Path:
    """Render a source exactly as build_photo_derivatives sees it before resize."""
    with open_frame(src) as raw:
        im = ImageOps.exif_transpose(raw)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        out = tmp / (src.stem + "-space.png")
        im.convert("RGB").save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", nargs="*", help="source images to inspect")
    ap.add_argument("--all", action="store_true",
                    help="inspect every source listed in SOURCES")
    args = ap.parse_args()

    if args.all:
        targets = [(resolve(e[0]), e[2]) for e in SOURCES]
    elif args.images:
        targets = [(pathlib.Path(p).expanduser(), None) for p in args.images]
    else:
        ap.error("give image paths or --all")

    found = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        qrfind = build_detector(tmp)
        for src, slug in targets:
            if not src.exists():
                print(f"MISS  {src}")
                continue
            space = masking_space(src, tmp)
            out = subprocess.run([str(qrfind), str(space)],
                                 capture_output=True, text=True).stdout
            boxes = []
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) < 3 or parts[1] == "clean":
                    continue
                boxes.append((parts[1], parts[2], parts[3]))
            if not boxes:
                continue
            found += len(boxes)
            label = slug or src.name
            print(f"\n{label}  ({src.name})")
            tuples = []
            for sym, box, payload in boxes:
                x, y, w, h = (float(v) for v in box.split())
                print(f"    {sym}  {payload}")
                tuples.append(f"({x:.5f}, {y:.5f}, {w:.5f}, {h:.5f})")
            print("    masks=(" + ", ".join(tuples) + ",)")

    print(f"\n{found} code(s) found in {len(targets)} source(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
