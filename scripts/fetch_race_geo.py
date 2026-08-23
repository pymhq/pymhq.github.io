"""Fetch the ground each race course is run over, from OpenStreetMap.

Why this exists
---------------
A course line on blank paper says nothing. The reason the Waterfront 5K is worth
a panel is that it runs down Alaskan Way with Elliott Bay on one side and the
ferry terminal in the way, and the only way to show that is to draw Alaskan Way
and Elliott Bay and the ferry terminal. So each race gets a real basemap: the
street network, the water, the parks and the railways inside its own frame.

Overpass is slow and rate limited and the panels get rebuilt over and over while
the drawing is tuned, so every response is cached raw under
~/.cache/pengandy-race-geo/<race>-<layer>.json and never fetched twice.

Stdlib only, matching the other scripts here.

Usage:
    python3 scripts/fetch_race_geo.py            # only what is missing
    python3 scripts/fetch_race_geo.py --force    # everything again
    python3 scripts/fetch_race_geo.py boston_10k # one race
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_courses as R          # noqa: E402

CACHE = Path.home() / ".cache" / "pengandy-race-geo"
COURSES = Path(__file__).resolve().parent.parent / "maps" / "data" / "races"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# The street classes worth drawing at 1:12,000. Service roads and driveways are
# left out: on the Seattle Center panel they were 40% of the file and read as a
# grey wash rather than as streets.
ROAD_CLASSES = ("motorway|motorway_link|trunk|trunk_link|primary|primary_link|"
                "secondary|secondary_link|tertiary|tertiary_link|residential|"
                "unclassified|living_street|pedestrian")
PATH_CLASSES = "footway|cycleway|path|steps|track|bridleway"

QUERIES = {
    "roads": '''[out:json][timeout:180];
way["highway"~"^({roads})$"]({s},{w},{n},{e});
out geom;''',
    "paths": '''[out:json][timeout:180];
way["highway"~"^({paths})$"]["area"!~"yes"]({s},{w},{n},{e});
out geom;''',
    "water": '''[out:json][timeout:180];
(
  way["natural"="water"]({s},{w},{n},{e});
  relation["natural"="water"]({s},{w},{n},{e});
  way["natural"="coastline"]({s},{w},{n},{e});
  way["waterway"="riverbank"]({s},{w},{n},{e});
);
out geom;''',
    "green": '''[out:json][timeout:180];
(
  way["leisure"~"^(park|garden|nature_reserve|pitch|golf_course)$"]({s},{w},{n},{e});
  relation["leisure"~"^(park|nature_reserve|golf_course)$"]({s},{w},{n},{e});
  way["landuse"~"^(forest|grass|meadow|cemetery|recreation_ground)$"]({s},{w},{n},{e});
  way["natural"="wood"]({s},{w},{n},{e});
);
out geom;''',
    "rail": '''[out:json][timeout:180];
way["railway"~"^(rail|light_rail|subway|tram|disused|abandoned)$"]({s},{w},{n},{e});
out geom;''',
}


def course_points(key: str) -> list:
    f = COURSES / f"{key}.json"
    return json.loads(f.read_text()) if f.exists() else []


def frame_of(race: dict) -> tuple[float, float, float, float]:
    """The frame a race is drawn in: its own course, with room round it.

    A course that fills its frame edge to edge has nowhere to put a start pin or
    a name, and the streets it turns off are the context that makes the turn
    legible. So the box is grown by a fifth of its own span, and never less than
    350 m, then squared up to the panel's aspect by the renderer.
    """
    if race.get("frame"):
        return race["frame"]
    pts = course_points(race["key"])
    if not pts and race.get("route"):
        pts = [(w[0], w[1]) for w in race["route"]["waypoints"]]
    if not pts:
        raise SystemExit(f"no course and no frame for {race['key']}")
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    s, n, w, e = min(lats), max(lats), min(lons), max(lons)
    mid = (s + n) / 2
    pad_lat = max((n - s) * 0.20, 350 / 110900)
    pad_lon = max((e - w) * 0.20, 350 / (111320 * math.cos(math.radians(mid))))
    return (w - pad_lon, s - pad_lat, e + pad_lon, n + pad_lat)


def run(name: str, query: str, bbox) -> dict:
    w, s, e, n = bbox
    body = query.format(s=s, w=w, n=n, e=e, roads=ROAD_CLASSES, paths=PATH_CLASSES)
    data = urllib.parse.urlencode({"data": body}).encode()
    last = None
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"User-Agent": "pengandy.com map build"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            wait = 8 * (attempt + 1)
            print(f"    {name}: {exc}; retry in {wait}s")
            time.sleep(wait)
    raise SystemExit(f"overpass failed for {name}: {last}")


def main() -> int:
    force = "--force" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    CACHE.mkdir(parents=True, exist_ok=True)
    for race in R.RACES:
        if only and race["key"] not in only:
            continue
        bbox = frame_of(race)
        print(f"{race['key']}  frame {tuple(round(v, 4) for v in bbox)}")
        for layer, query in QUERIES.items():
            out = CACHE / f"{race['key']}-{layer}.json"
            if out.exists() and not force:
                print(f"    {layer}: cached ({out.stat().st_size // 1024} KB)")
                continue
            got = run(layer, query, bbox)
            out.write_text(json.dumps(got))
            print(f"    {layer}: {len(got.get('elements', []))} elements, "
                  f"{out.stat().st_size // 1024} KB")
            time.sleep(1.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
