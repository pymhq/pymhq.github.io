"""Fetch the real-world geometry that panel 2.5 of maps.html is drawn from.

Panel 2 is a hand-drawn chart: its coastlines are invented curves that put
each place where the composition wanted it. Panel 2.5 is the same content on
a true map, so it needs real data. This pulls it from OpenStreetMap through
Overpass and caches the raw responses, because Overpass is slow and rate
limited and the build script is run over and over while the drawing is tuned.

Layers fetched, all clipped to the Salish Sea frame:
    coastline   natural=coastline ways   -> land polygons
    water       named lakes/reservoirs   -> freshwater cutouts
    rivers      named rivers             -> the blue threads
    roads       I-5, US-101, WA-20 ...   -> the drive routes
    parks       Olympic / North Cascades -> park boundaries

Stdlib only, matching the conventions of scripts/*.py.

Usage:
    python3 scripts/fetch_salish_geo.py [--force]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CACHE = Path.home() / ".cache" / "pengandy-salish-geo"

# The frame: Cape Flattery to Washington Pass, Olympia to the Gulf Islands.
# Every place named on panel 2 falls inside it, including the ones panel 2
# had to fake (the Cascade crest) or crop (the Pacific shore).
SOUTH, WEST, NORTH, EAST = 46.80, -124.90, 49.16, -120.50

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# The coastline of an archipelago is the one layer big enough to time the
# whole-frame query out, so it is fetched tile by tile. `out geom` returns
# every way that touches a tile whole, so tiling costs nothing but repeats:
# ways are deduplicated by id on the way in.
COAST_TILES = (4, 4)

LAKE_NAMES = (
    "Lake Washington|Lake Union|Lake Sammamish|Green Lake|Lake Crescent|"
    "Lake Cushman|Ross Lake|Diablo Lake|Lake Quinault|Wynoochee Lake|"
    "Rattlesnake Lake|Baker Lake|Lake Whatcom|Union Bay|Portage Bay|"
    "Gorge Lake|Lake Shannon|American Lake|Lake Chelan|Lake Stevens|"
    "Lake Youngs|Chester Morse Lake|Bumping Lake|Kachess Lake|"
    "Cle Elum Lake|Keechelus Lake|Silver Lake|Lake Tapps|Riffe Lake|"
    "Lake Ozette|Lake Sutherland|Anderson Lake|Cranberry Lake"
)

RIVER_NAMES = (
    "Skagit River|Nooksack River|Skykomish River|Snoqualmie River|"
    "Green River|Elwha River|Dosewallips River|Skokomish River|"
    "Chehalis River|Sammamish River|Duwamish River|Cedar River|"
    "Hoh River|Quinault River|Stillaguamish River|Snohomish River|"
    "White River|Puyallup River|Nisqually River|Deschutes River|"
    "Dungeness River|Hamma Hamma River|Wynoochee River|Humptulips River|"
    "Queets River|Bogachiel River|Sol Duc River|Calawah River|"
    "Baker River|Sauk River|Suiattle River|Samish River|"
    "Tolt River|Raging River|Issaquah Creek|Ship Canal"
)

# Only the routes panel 2 actually drives, plus the two passes it names.
# Only the routes panel 2 actually drives, plus the two passes it names.
# Washington signs its state routes SR in OSM, not WA, which is worth knowing
# before wondering why a whole island has no roads on it.
ROAD_REFS = "I 5|I 90|I 405|US 2|US 101|US 12|SR [0-9]+|WA [0-9]+"

QUERIES = {
    "coastline": '''[out:json][timeout:600];
way["natural"="coastline"]({s},{w},{n},{e});
out geom;''',
    "water": '''[out:json][timeout:600];
(
  way["natural"="water"]["name"~"^({lakes})$"]({s},{w},{n},{e});
  relation["natural"="water"]["name"~"^({lakes})$"]({s},{w},{n},{e});
  way["waterway"="canal"]["name"~"Ship Canal|Swinomish"]({s},{w},{n},{e});
);
out geom;''',
    "rivers": '''[out:json][timeout:600];
way["waterway"~"^(river|canal)$"]["name"~"^({rivers})$"]({s},{w},{n},{e});
out geom;''',
    "roads": '''[out:json][timeout:900];
way["highway"~"^(motorway|trunk|primary|secondary)$"]["ref"~"^({refs})$"]({s},{w},{n},{e});
out geom;''',
    # Interchanges are built of ramps, and a ramp carries no route number, so
    # without this layer the routed drives cannot get from I-5 onto SR-20 at
    # all: the two highways share no node, only a bridge.
    "links": '''[out:json][timeout:900];
way["highway"~"_link$"]({s},{w},{n},{e});
out geom;''',
    "parks": '''[out:json][timeout:600];
relation["boundary"~"^(protected_area|national_park)$"]["name"~"^(Olympic National Park|North Cascades National Park|Mount Rainier National Park|Ross Lake National Recreation Area)$"]({s},{w},{n},{e});
out geom;''',
}


def run(name: str, query: str, bbox=None) -> dict:
    s, w, n, e = bbox or (SOUTH, WEST, NORTH, EAST)
    body = query.format(
        s=s, w=w, n=n, e=e,
        lakes=LAKE_NAMES, rivers=RIVER_NAMES, refs=ROAD_REFS,
    )
    data = urllib.parse.urlencode({"data": body}).encode()
    last = None
    for attempt in range(8):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={"User-Agent": "pengandy.com map build"})
            with urllib.request.urlopen(req, timeout=900) as resp:
                payload = json.loads(resp.read().decode())
            if "elements" in payload:
                # An inland tile legitimately has no coastline in it.
                print(f"  {name}: {len(payload['elements'])} elements from {url}")
                return payload
            last = "no elements key"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError) as exc:
            last = exc
        wait = 10 * (attempt + 1)
        print(f"  {name}: attempt {attempt + 1} failed ({last}); retrying in {wait}s")
        time.sleep(wait)
    raise SystemExit(f"{name}: giving up ({last})")


def fetch_tiled(name: str, query: str) -> dict:
    """Same query over a grid, merged: one giant bbox times Overpass out."""
    cols, rows = COAST_TILES
    seen: dict[int, dict] = {}
    for r in range(rows):
        for c in range(cols):
            s = SOUTH + (NORTH - SOUTH) * r / rows
            n = SOUTH + (NORTH - SOUTH) * (r + 1) / rows
            w = WEST + (EAST - WEST) * c / cols
            e = WEST + (EAST - WEST) * (c + 1) / cols
            tile = f"{name}[{c},{r}]"
            try:
                payload = run(tile, query, (s, w, n, e))
            except SystemExit:
                # A tile can be pure land or pure water: nothing to return.
                print(f"  {tile}: empty")
                continue
            for el in payload["elements"]:
                seen.setdefault(el.get("id"), el)
            time.sleep(2)
    print(f"  {name}: {len(seen)} unique ways")
    return {"elements": list(seen.values())}


def main() -> int:
    force = "--force" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, query in QUERIES.items():
        if only and name not in only:
            continue
        out = CACHE / f"{name}.json"
        if out.exists() and not force:
            print(f"  {name}: cached ({out.stat().st_size // 1024} KB)")
            continue
        print(f"fetching {name} ...")
        payload = fetch_tiled(name, query) if name in ("coastline", "roads", "links") else run(name, query)
        out.write_text(json.dumps(payload))
        print(f"  {name}: wrote {out.stat().st_size // 1024} KB")
        time.sleep(4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
