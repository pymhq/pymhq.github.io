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
    local_roads named-but-unnumbered roads, and Vashon whole
    rockies_roads  BC/Alberta 1, 93, 99, 16 -> the Canadian drives
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
# Washington signs its state routes SR in OSM, not WA, which is worth knowing
# before wondering why a whole island has no roads on it.
ROAD_REFS = "I 5|I 90|I 405|US 2|US 101|US 12|SR [0-9]+|WA [0-9]+"

# The roads that carry a drive on these sheets and no route number to be found
# by. The `roads` layer asks for motorway..secondary with a ref, which is the
# right net for a highway and the wrong one for the last 20 km of a day out: the
# spur up to a trailhead is `tertiary` with a name and nothing else, so Sol Duc,
# the Hoh, Hurricane Ridge and Rialto were unreachable and Paradise was outside
# the frame besides. Each of these is a road actually driven, named here so the
# router can put the line on it instead of a hand-typed curve pretending to be
# routed.
LOCAL_ROAD_NAMES = (
    # the Olympic park spurs
    "Hurricane Ridge Road|Sol Duc Hot Springs Road|Upper Hoh Road|Mora Road|"
    # Rainier: SR 706 stops at the Nisqually entrance and the park names its own
    "Nisqually Entrance to Longmire Road|Longmire-to-Paradise Road|"
    "Stevens Canyon Road|"
    # the two foothill trailheads out of Seattle
    "Issaquah Hobart Road Southeast|Front Street South|"
    "Cedar Falls Road Southeast|Cedar Falls Road|"
    # West Seattle, because the bridge to it carries no number at all
    "West Seattle Bridge|Fauntleroy Way Southwest|"
    "South Spokane Street|Southwest Spokane Street"
)
# SR 706 is the National Park Highway up to Longmire and Paradise, and SR 7 is
# how you reach it. Both carry a number, so `roads` would have caught them,
# except that they run below 46.80 and the Salish frame stops there: the whole
# southwest entrance to Rainier was one tenth of a degree off the bottom of the
# fetch. SR 110 Spur is Mora Road out to Rialto, and the ` Spur` suffix is why
# the `SR [0-9]+` pattern never matched it.
LOCAL_ROAD_REFS = "SR 7|SR 706|SR 110 Spur"
# Vashon and Maury, whole, plus the four junctions where a numbered highway
# hands over to a road with only a name. A drive is routed on a graph, and a
# graph is only connected where two ways share a node: US-101 does not touch
# Hurricane Ridge Road (Race Street is between them), SR 706 stops at the
# Nisqually gate, I-90 does not touch Cedar Falls Road, and I-90 does not touch
# Issaquah Hobart Road. Naming every connector one at a time is a guessing game,
# so each junction gets a small box and the box gets the local net entire.
LOCAL_BOXES = (
    # Vashon and Maury: one island, 5 km by 20, and not one numbered route on
    # it. The ferry lands at Vashon Heights and the rest is Vashon Highway SW.
    (47.35, -122.56, 47.53, -122.36),
    # Port Angeles, where US-101 hands over to Race Street and the ridge road.
    (48.08, -123.47, 48.13, -123.39),
    # The Nisqually entrance up to Paradise, inside Rainier.
    (46.72, -122.02, 46.82, -121.68),
    # I-90 exit 32 down to Rattlesnake Lake.
    (47.40, -121.84, 47.47, -121.73),
    # Issaquah, from I-90 to the foot of Issaquah Hobart Road.
    (47.50, -122.07, 47.57, -121.98),
)

# Canada. The `roads` layer stops at the 49th parallel because the Salish frame
# does, so the Canada sheet had a Sea to Sky highway with no highway on it and a
# Rockies loop drawn as nothing at all. These are the roads that trip was: 99 up
# Howe Sound to Whistler, 1 from Vancouver through Banff to Calgary, 93 the
# Icefields Parkway from Lake Louise to Jasper, 16 the Yellowhead through it.
#
# The optional prefix is the whole trick, and it took three tries to find. BC
# tags the southern Sea to Sky `99` and the half north of Squamish `BC 99`;
# through Yoho the Trans-Canada is `TCH 1`, so asking for `1` alone leaves a
# 30 km hole in it either side of Field and no way to drive to Yoho at all.
CA_ROAD_REFS = "(BC |AB |TCH )?(1|1A|2|16|93|93A|99)"
# Downtown Vancouver to Horseshoe Bay: Georgia Street, the causeway and the
# Lions Gate Bridge are what joins the city end of Highway 99 to the Sea to Sky,
# and without them the two halves of `BC 99` are two disconnected components.
# The second box is the Bow valley, Banff to Lake Louise, where the Trans-Canada
# is twinned and fenced and comes back from Overpass in two pieces that share no
# node: with only the numbered ways, Yoho and the Icefields Parkway sit on the
# far side of a break in the one highway that reaches them.
CA_BOXES = (
    (49.26, -123.32, 49.40, -123.02),
    (51.10, -116.35, 51.52, -115.45),
)
ROCKIES_BOX = (48.20, -123.80, 53.45, -113.60)

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
    # The named-but-unnumbered roads, plus the local net of each junction box.
    # `residential` is in the net inside a box and nowhere else: on Vashon the
    # road to the lighthouse is residential, and without it Maury has no roads.
    "local_roads": '''[out:json][timeout:900];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)$"]["name"~"^({names})$"]({s},{w},{n},{e});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]["ref"~"^({local_refs})$"]({s},{w},{n},{e});
{boxes}
);
out geom;''',
    # Canada: Howe Sound to the continental divide, and the Icefields Parkway.
    # The ramps come too, because a Canadian interchange is built of ramps and
    # without them Highway 1 and Highway 93 never meet.
    "rockies_roads": '''[out:json][timeout:900];
(
  way["highway"~"^(motorway|trunk|primary|secondary)$"]["ref"~"^({ca_refs})$"]({s},{w},{n},{e});
  way["highway"~"_link$"]({s},{w},{n},{e});
{ca_boxes}
);
out geom;''',
}


def box_queries(boxes, classes: str, plain: str) -> str:
    """One box, three sub-queries: the named net, the unnamed net, the ramps.

    The unnamed pass is not padding. A junction is often built of one unnamed
    stub - the entrance station road at Rainier is 174 m of way with no name and
    no number - and asking only for named roads leaves the park's whole road
    system as an island the router cannot reach.
    """
    out = []
    for s, w, n, e in boxes:
        bb = f"{s},{w},{n},{e}"
        out.append(f'  way["highway"~"^({classes})$"]["name"]({bb});')
        out.append(f'  way["highway"~"^({plain})$"]({bb});')
        out.append(f'  way["highway"~"_link$"]({bb});')
    return "\n".join(out)


# Layers cut from a frame of their own. Everything else takes the Salish frame.
BBOXES = {
    # South to 46.70 so SR 706 and Paradise are inside it.
    "local_roads": (46.70, -124.90, 49.16, -120.50),
    "rockies_roads": ROCKIES_BOX,
}


def run(name: str, query: str, bbox=None) -> dict:
    s, w, n, e = bbox or BBOXES.get(name) or (SOUTH, WEST, NORTH, EAST)
    body = query.format(
        s=s, w=w, n=n, e=e,
        lakes=LAKE_NAMES, rivers=RIVER_NAMES, refs=ROAD_REFS,
        names=LOCAL_ROAD_NAMES, local_refs=LOCAL_ROAD_REFS, ca_refs=CA_ROAD_REFS,
        boxes=box_queries(LOCAL_BOXES,
                          "secondary|tertiary|unclassified|residential",
                          "secondary|tertiary|unclassified"),
        ca_boxes=box_queries(CA_BOXES,
                             "motorway|trunk|primary|secondary|tertiary",
                             "motorway|trunk|primary|secondary|tertiary"),
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
