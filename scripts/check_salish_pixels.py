#!/usr/bin/env python3
"""Check the rendered pixels, not the markup.

Three separate bugs got past every geometry and collision check because none of
them looked at what colour a place ends up: the Olympic Peninsula drawn as open
water, Bellevue drawn as open sea, and the whole US mainland missing from the
index sheet because the frame-closing quietly dropped the coastline pieces that
end inland.

So this renders each sheet and samples the pixel at a set of known positions.
Land must be land, water must be water, a place I have not been to must be the
lighter tone -- on every sheet that shows it, identically -- and an island must
be one tone all over, which is the check that the wash boxes could never pass.

Needs Chrome and Pillow. Run after scripts/build_salish_geo_panel.py.

Usage:
    python3 scripts/check_salish_pixels.py
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import salish_places as P  # noqa: E402
from salish_geo import Proj, in_ring, is_dry, island_rings  # noqa: E402

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
    # Vancouver Island is one landmass and I have set foot on it: the ferry from
    # Tsawwassen lands at Swartz Bay and Victoria is on it. It used to be washed
    # back with a disc of full colour punched through at Victoria, which is the
    # kind of half-and-half only the Kitsap gets now, and only because a 60 km
    # peninsula touched at one town cannot honestly be either tone.
    ("Vancouver Island", 48.6000, -123.9000, "land"),
    ("Victoria", 48.4300, -123.3600, "land"),
    # The Kitsap is the one exception to a tone per landmass: the peninsula is
    # the lighter tone and Poulsbo stands on it in full colour. Both halves of
    # that are sampled, and so is the mainland across the water from it, because
    # the failure mode of the old wash was a polygon reaching the wrong shore.
    ("Poulsbo", 47.7362, -122.6465, "land"),
    ("Bremerton, Kitsap", 47.5673, -122.6329, "faded"),
    ("Gig Harbor peninsula", 47.3450, -122.6050, "faded"),
    ("Hood Canal, Olympic side", 47.6000, -123.0400, "land"),
    ("Shelton, past the isthmus", 47.2151, -123.1007, "land"),
    ("Lopez", 48.4800, -122.8800, "faded"),
    ("Shaw", 48.5780, -122.9300, "faded"),
    ("Blake Island", 47.5390, -122.4930, "faded"),
    ("Lummi Island", 48.6800, -122.6500, "faded"),
    ("Camano Island", 48.1900, -122.4700, "faded"),
    ("Salt Spring, BC", 48.8300, -123.4830, "faded"),
    ("mid Puget Sound", 47.9000, -122.4000, "water"),
    ("mid Rosario Strait", 48.5350, -122.7350, "water"),
    ("mid Lake Washington", 47.6200, -122.2500, "water"),
]

# One island, one tone. The islands whose colour is the point of the rule, by a
# point inside each; the sample points themselves are worked out from the
# island's own coastline below, because hand-picked ones kept landing in the
# water: the reference point for Orcas sits in East Sound and the one for Whidbey
# in Penn Cove, and a fjord is not a counter-example to anything.
ISLANDS = [
    ("Whidbey", 48.2201, -122.6857, "land"),
    ("San Juan Island", 48.5300, -123.0700, "land"),
    ("Orcas", 48.6600, -122.9200, "land"),
    ("Fidalgo", 48.4900, -122.6300, "land"),
    ("Bainbridge", 47.6480, -122.5450, "land"),
    ("Vashon", 47.4300, -122.4650, "land"),
    ("Lopez", 48.4800, -122.8800, "faded"),
    ("Camano", 48.2000, -122.5000, "faded"),
    ("Lummi", 48.6800, -122.6500, "faded"),
    ("Salt Spring, BC", 48.8300, -123.4830, "faded"),
]

# How far a sample has to be from any shore. In km, so a point is only sampled at
# all where the sheet's own scale puts it clear of the 8-unit coast glow: on the
# Canada sheet at 1.6 units per km, Lopez is nine units across and there is no
# such point on it, so it is not sampled there rather than sampled wrongly.
CLEAR_UNITS = 9.0

# shore_km is a scan of a coastline ring per point, so the answers are kept.
CLEAR: dict = {}


# Sample points are chosen for distance from the shore, not by hand: the coast
# glow is an 8-unit stroke, which is a kilometre of ground on a 7 u/km sheet, and
# a point nearer than that to the water reads as neither land nor water.
def classify(c) -> str:
    if abs(c[0] - LAND[0]) < 26 and abs(c[1] - LAND[1]) < 26 and c[2] < 150:
        return "land"
    if c[0] > 226 and c[1] > 230:
        return "water"
    return "faded"


def patch(im, x, y, r=4):
    """The tone of the paper under this point, or None where something is drawn.

    A single pixel is no use on a sheet that also carries names and drawings: type
    is set with a 3px halo in the water colour, so one pixel of a label reads as
    water on dry land. So a 9x9 patch has to agree with itself, and any ink in it
    - type, a doodle's outline, a route - disqualifies the point. What is left is
    paper, which is the only thing this file is asking about.
    """
    counts: dict[str, int] = {}
    n = 0
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            c = im.getpixel((x + dx, y + dy))
            if c[0] < 100 or (c[2] > c[0] + 20):     # ink, or something blue
                return None
            k = classify(c)
            counts[k] = 1 + counts.get(k, 0)
            n += 1
    top = max(counts, key=counts.get)
    return top if counts[top] >= 0.9 * n else None


def km_between(a, b) -> float:
    """(lat, lon) to (lat, lon), in km."""
    return math.hypot((b[0] - a[0]) * 110.9,
                      (b[1] - a[1]) * 111.32 * math.cos(math.radians(a[0])))


def island_of(lat, lon):
    """The island ring holding this point: the smallest one that contains it."""
    holding = [r for r in island_rings() if in_ring((lon, lat), r)]
    return min(holding, key=B.ring_span_km) if holding else None


def inland_points(ring, want=8):
    """Points inside this island, sorted by how far they are from its shore.

    A grid over the island's own bounding box, each candidate kept if it is inside
    the ring, with the distance to the nearest point of the outline attached. That
    distance is what decides, per sheet, whether the point is far enough from the
    coast glow to be worth sampling.
    """
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    step = max(1, len(ring) // 600)
    outline = [(la, lo) for lo, la in ring[::step]]
    out = []
    for i in range(1, 12):
        for j in range(1, 12):
            lo = min(xs) + (max(xs) - min(xs)) * i / 12
            la = min(ys) + (max(ys) - min(ys)) * j / 12
            # is_dry, not just inside the ring: an island can hold a lake, and
            # Lake Campbell on Fidalgo is water and is drawn as water.
            if not in_ring((lo, la), ring) or not is_dry((lo, la)):
                continue
            d = min(km_between((la, lo), q) for q in outline)
            out.append((d, la, lo))
    out.sort(reverse=True)
    return out[:want]


def shore_km(lat, lon) -> float:
    """How far this point is from the shore of the island it stands on.

    Infinite on the mainland, which no sheet in this set ever shows small enough
    for the coast glow to swallow. On an island it is the number that says whether
    a given sheet draws that island big enough to sample: Lopez is 9 units across
    on the Canada sheet and the glow alone is 8 of them.
    """
    ring = island_of(lat, lon)
    if ring is None:
        return float("inf")
    step = max(1, len(ring) // 600)
    return min(km_between((lat, lon), (la, lo)) for lo, la in ring[::step])


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
            if CLEAR.setdefault((lat, lon), shore_km(lat, lon)) \
                    * proj.px_per_km() < CLEAR_UNITS:
                continue
            x, y = proj(lon, lat)
            if not (mx + 6 < x < mx + mw - 6 and 6 < y < 894):
                continue
            got = patch(im, int(x), int(y))
            if got is None:
                continue
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

    print("\n=== one island, one tone ===")
    spreads = []
    for name, lat, lon, want in ISLANDS:
        ring = island_of(lat, lon)
        if ring is None:
            fails.append(f"{name} is inside no island ring")
            print(f"  BAD {name}: in no island ring")
            continue
        spreads.append((name, want, inland_points(ring)))
    for i, sheet in enumerate(P.SHEETS, 1):
        im = Image.open(Path(f"/tmp/salish_px{i}.png")).convert("RGB")
        frame = sheet["frame"]
        mx, mw, mh = B.sheet_geometry(frame)
        proj = Proj(frame[0], frame[1], frame[2], frame[3], mx, 0, mw, mh)
        upk = proj.px_per_km()
        for name, want, pts in spreads:
            got = {}
            for d, lat, lon in pts:
                if d * upk < CLEAR_UNITS:
                    continue
                if not (frame[1] <= lat <= frame[3] and frame[0] <= lon <= frame[2]):
                    continue
                x, y = proj(lon, lat)
                if not (mx + 6 < x < mx + mw - 6 and 6 < y < 894):
                    continue
                tone = patch(im, int(x), int(y))
                if tone is None:
                    continue
                got[(round(lat, 3), round(lon, 3))] = tone
            if len(got) < 2:
                continue
            checked += len(got)
            tones = set(got.values())
            ok = tones == {want}
            if not ok:
                fails.append(f"{sheet['key']}: {name} is not one tone: {got}")
            print(f"  {'ok ' if ok else 'BAD'} {sheet['key']:9} {name:16} "
                  f"{len(got)} points, {sorted(tones)}")

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
