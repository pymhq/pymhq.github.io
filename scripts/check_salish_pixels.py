#!/usr/bin/env python3
"""Check the rendered pixels, not the markup.

Three separate bugs got past every geometry and collision check because none of
them looked at what colour a place ends up: the Olympic Peninsula drawn as open
water, Bellevue drawn as open sea, and the whole US mainland missing from the
index sheet because the frame-closing quietly dropped the coastline pieces that
end inland.

So this renders each sheet and samples the pixel at a set of known positions.
Land must be land, water must be water, and a place I have not been to must be
half transparent -- on every sheet that shows it, identically.

Needs Chrome and Pillow. Run after scripts/build_salish_geo_panel.py.

Usage:
    python3 scripts/check_salish_pixels.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import salish_places as P  # noqa: E402
from salish_geo import Proj  # noqa: E402

import build_salish_geo_panel as B  # noqa: E402

CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

LAND = (141, 155, 99)
WATER = (238, 242, 234)

# (name, lat, lon, expected) where expected is land | water | faded
# Sampling open water only works where the water is wider than the 8-unit coast
# glow; on the index sheet Elliott Bay is not, so it is left to the Seattle sheet.
POINTS = [
    ("Olympic interior", 47.80, -123.60, "land"),
    ("Hoh Rain Forest", 47.8350, -123.9050, "land"),
    ("Seattle", 47.6200, -122.3000, "land"),
    ("Kirkland", 47.6800, -122.1900, "land"),
    ("Cascade foothills", 47.6000, -121.3000, "land"),
    ("Skagit flats", 48.4000, -122.2500, "land"),
    ("Whidbey", 48.3820, -122.4140, "land"),
    ("Bainbridge", 47.6480, -122.5450, "land"),
    ("Vashon", 47.4300, -122.4650, "land"),
    ("San Juan Island", 48.5500, -123.1000, "land"),
    ("Orcas", 48.6500, -122.8250, "land"),
    ("Fidalgo", 48.4900, -122.6300, "land"),
    # Only Victoria on Vancouver Island is mine; the rest of it is not.
    ("Vancouver Island", 48.6000, -123.9000, "faded"),
    ("Victoria", 48.4300, -123.3600, "land"),
    ("Lopez", 48.4800, -122.8800, "faded"),
    ("Shaw", 48.5780, -122.9300, "faded"),
    ("Blake Island", 47.5390, -122.4930, "faded"),
    ("Lummi Island", 48.6800, -122.6500, "faded"),
    ("Bremerton, Kitsap", 47.5673, -122.6329, "faded"),
    ("Gig Harbor peninsula", 47.3450, -122.6050, "faded"),
    ("mid Puget Sound", 47.9000, -122.4000, "water"),
    ("mid Rosario Strait", 48.5350, -122.7350, "water"),
    ("mid Lake Washington", 47.6200, -122.2500, "water"),
]


# Sample points are chosen for distance from the shore, not by hand: the coast
# glow is an 8-unit stroke, which is a kilometre of ground on a 7 u/km sheet, and
# a point nearer than that to the water reads as neither land nor water.
def classify(c) -> str:
    if abs(c[0] - LAND[0]) < 26 and abs(c[1] - LAND[1]) < 26 and c[2] < 150:
        return "land"
    if c[0] > 226 and c[1] > 230:
        return "water"
    return "faded"


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("needs Pillow: pip install pillow")
        return 2

    fails, checked = [], 0
    seen: dict[str, dict[str, str]] = {}
    for i, sheet in enumerate(P.SHEETS, 1):
        html = Path(f"/tmp/salish_sheet{i}.html")
        if not html.exists():
            print(f"missing {html}; run the build first")
            return 2
        png = Path(f"/tmp/salish_px{i}.png")
        subprocess.run([CHROME, "--headless", "--disable-gpu",
                        "--force-device-scale-factor=1", "--window-size=1600,900",
                        "--hide-scrollbars", f"--screenshot={png}", str(html)],
                       capture_output=True)
        if not png.exists():
            print(f"could not render sheet {i}")
            return 2
        im = Image.open(png).convert("RGB")
        frame = sheet["frame"]
        mx, mw, mh = B.sheet_geometry(frame)
        proj = Proj(frame[0], frame[1], frame[2], frame[3], mx, 0, mw, mh)
        print(f"\n=== sheet {i}: {sheet['key']} ===")
        for name, lat, lon, want in POINTS:
            if not (frame[1] <= lat <= frame[3] and frame[0] <= lon <= frame[2]):
                continue
            x, y = proj(lon, lat)
            if not (mx + 3 < x < mx + mw - 3 and 3 < y < 897):
                continue
            got = classify(im.getpixel((int(x), int(y))))
            checked += 1
            seen.setdefault(name, {})[sheet["key"]] = got
            ok = got == want
            if not ok:
                fails.append(f"{sheet['key']}: {name} is {got}, expected {want}")
            print(f"  {'ok ' if ok else 'BAD'} {name:20} {got:6} (want {want})")

    print("\n=== the same place must look the same on every sheet ===")
    for name, states in sorted(seen.items()):
        vals = set(states.values())
        if len(vals) > 1:
            fails.append(f"{name} differs by sheet: {states}")
            print(f"  BAD {name:20} {states}")
    print(f"  {len(seen)} places, "
          f"{sum(1 for s in seen.values() if len(set(s.values())) == 1)} consistent")

    print("\n" + "=" * 60)
    print(f"{checked} pixel checks")
    if fails:
        print(f"FAILURES: {len(fails)}")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("every sampled place is the right colour, on every sheet that shows it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
