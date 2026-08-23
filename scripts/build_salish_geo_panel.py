"""Build the to-scale Salish Sea sheet in maps.html.

Panel 2 of maps.html draws this coast by hand, with the geography bent to suit
the page: the Cascade crest pulled in to half its true distance, Lopez shrunk to
an ellipse, Seattle's parks spread along a mile of invented shoreline. This
sheet keeps every place and every doodle and gives up the bending. One Mercator
window, one scale, real coastlines, lakes, rivers and highways from
OpenStreetMap.

The arithmetic that shapes the design: a doodle is 20 to 44 units wide, and the
sheet is 3.6 units per km, so a glyph covers 6 to 12 km of ground. Anything
closer together than that cannot carry two doodles at once. Rather than move the
places, as panel 2 does, or cut the sheet into an atlas, the sheet draws as many
doodles at true positions as physically fit and gathers the overflow into
clusters: a badge with a count, which opens on hover, tap or keyboard focus into
a ring of its members, each on a leader back to its true point. Nothing is
moved without a thread saying so.

    python3 scripts/build_salish_geo_panel.py             # write into maps.html
    python3 scripts/build_salish_geo_panel.py --preview   # /tmp preview only

The sheet is written between the BEGIN/END marker comments in maps.html, so
re-running is idempotent. The glyphs are not copied by hand: the <defs> block of
panel 2 is lifted out of maps.html at build time and re-emitted with an sg-
prefix, so the doodles on the two charts cannot drift apart.
"""

from __future__ import annotations

import heapq
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import salish_places as P  # noqa: E402
from salish_geo import (  # noqa: E402
    Proj, clip_chain, clip_ring, in_ring, is_dry, land_rings, load, merc_y, num,
    WaterGrid, on_land, path_d, points_d, rdp, snap_to, stitch, way_coords,
)

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps.html"

BEGIN = "<!-- BEGIN generated: salish sea to scale (scripts/build_salish_geo_panel.py) -->"
END = "<!-- END generated: salish sea to scale -->"

# The sheet is 16:9, which is the shape of the screen it fills. The map itself
# is 1157 x 900: its width follows from its height, because the height is the
# latitude range and the scale is uniform. The rest is apron, and the apron is
# the point of the wide sheet: on panel 2 the title, the legend and the insets
# all sit on top of the water. Here nothing covers the chart.
VB_W, VB_H = 1600.0, 900.0

# The overview frame is cut to what the chart is about. West of the Hoh and south
# of Tacoma there is nothing on panel 2 but the Pacific shore and the state
# capital, and carrying them cost the whole sheet a fifth of its scale: the
# screen limits height, so 50 km of latitude nobody needed was 50 km of
# everybody else shrunk.


# The apron carries the title, the note, the bar, the legend and the locator: it
# needs about 280 units, and 60 more to stay clear of the map.
APRON_MIN = 340.0
# The right apron carries the credit, so it needs room of its own.
APRON_RIGHT = 170.0


def sheet_geometry(frame, height=VB_H, share=0.66):
    """Fit a frame into a sheet: the map takes the height, the slack is apron.

    A wide frame can ask for more width than the sheet has left once the apron is
    paid for. The index sheet reached 1332 units and left 177 for an apron that
    needs 340, so its text was printed on top of the map. When that happens the
    map gives up height instead, which keeps the scale uniform.
    """
    w, s, e, n = frame
    span = (math.radians(e) - math.radians(w)) / (merc_y(n) - merc_y(s))
    map_w = height * span
    if map_w > VB_W - APRON_MIN - APRON_RIGHT:
        map_w = VB_W - APRON_MIN - APRON_RIGHT
        height = map_w / span
    map_w = round(map_w, 1)
    map_x = round(max((VB_W - map_w) * share, APRON_MIN), 1)
    return map_x, map_w, round(height, 1)


def on_frame(lat: float, lon: float, frame, pad: float = 0.0) -> bool:
    w, s, e, n = frame
    return s + pad <= lat <= n - pad and w + pad <= lon <= e - pad


def overview_frame():
    return next(s["frame"] for s in P.SHEETS if s["key"] == "overview")


def sheet_frames(sheet) -> list[tuple]:
    """Every piece of ground a sheet draws. One frame each, since the town plans
    went: a sheet is a window on the ground, not a page of little windows."""
    return [sheet["frame"]]


# --------------------------------------------------------------------- glyphs
# Panel 2 draws five things inline instead of in its defs: the Hurricane Ridge
# snowfield and the volcano cones. They are copied here so the same hand appears
# on both charts; Rainier is the Glacier Peak cone, which is the one panel 2
# never had room to draw.
INLINE_GLYPHS = {
    "ridge": '''<path class="rt-doodle" fill="#7d8f5c" d="M -15 8 C -10 2, -7 -3, -2 -6 C 1 -7.5, 4 -6, 6 -3 C 9 1, 12 5, 15 8 Z"/>
<path class="rt-doodle" fill="#f7f1e0" d="M -4.5 -4.5 C -3 -6, 0 -7, 2 -6 C 3 -5.2, 3.5 -4, 4 -3 Q 1 -1.5, -1 -3 Q -3 -2, -4.5 -4.5 Z"/>''',
    "baker": '''<path class="rt-doodle" fill="#7d8f5c" d="M -34 22 C -22 4, -14 -10, -6 -20 C -2 -25, 2 -25, 6 -20 C 14 -10, 22 4, 34 22 Z"/>
<path class="rt-doodle" fill="#7d8f5c" d="M 18 22 C 25 13, 31 7, 37 3 C 43 9, 47 15, 49 22 Z"/>
<path class="rt-doodle" fill="#f7f1e0" d="M -11 -13 C -8 -17.5, -4 -21, 0 -21 C 4 -21, 8 -17.5, 11 -13 C 7 -9.5, 4 -12, 0 -9.5 C -4 -12, -7 -9.5, -11 -13 Z"/>
<path class="rt-doodle" fill="none" stroke-width="1.1" d="M -5 -10.5 q 1 3 0 5.5 M 5 -10.5 q 1 3 0 5.5"/>''',
    "shuksan": '''<path class="rt-doodle" stroke-width="1.3" fill="#7d8f5c" d="M -26 18 C -20 8, -15 -2, -11 -8 C -8.6 -11.4, -6.4 -10.6, -4.6 -6 C -3 -2.4, -1.4 0.6, 0 3 C 1.4 -1, 2.6 -8, 5 -14 C 7 -18.6, 10 -18.6, 12 -14 C 15 -7, 19 4, 24 12 C 25.6 14.6, 26.6 16.6, 27 18 Z"/>
<path class="rt-doodle" stroke-width="1" fill="#f7f1e0" d="M 5 -14 C 6.6 -17.4, 9.6 -17.4, 11 -13.4 C 12 -11, 13 -8.6, 13.6 -7 C 11 -5.4, 8.6 -7.4, 6 -6 C 5 -8.6, 4 -11, 5 -14 Z"/>
<path class="rt-doodle" stroke-width="0.9" fill="#f7f1e0" d="M -11 -8 C -9.4 -11, -7 -11, -5.6 -7.4 C -4.6 -5.4, -4 -3.6, -3.4 -2.6 C -5.6 -1, -7.4 -3, -9.4 -1.6 C -10.4 -3.6, -11 -5.6, -11 -8 Z"/>''',
    "cone": '''<path class="rt-doodle" fill="#7d8f5c" d="M -32 22 C -21 5, -13 -11, -5 -21 C -1 -26, 3 -26, 7 -21 C 15 -11, 23 5, 34 22 Z"/>
<path class="rt-doodle" fill="#f7f1e0" d="M -10 -12 C -7.5 -16.5, -4 -20, 1 -20 C 5 -20, 8.5 -16.5, 11 -12 C 7 -8.5, 4 -11, 1 -8.5 C -3 -11, -6 -8.5, -10 -12 Z"/>
<path class="rt-doodle" fill="none" stroke-width="1" d="M -5 -21 L -12 22 M 7 -21 L 14 22"/>''',
    "orca": '''<path class="rt-orca" d="M -14 2 Q -8 -7 2 -7 Q 11 -7 13 -1 Q 13 3 7 4 L -8 4 Q -14 4 -14 2 Z"/>
<path class="rt-orca" d="M -13 2 Q -17 -2 -20 -4 Q -18 2 -20 6 Q -16 4 -12 4 Z"/>
<path class="rt-orca" d="M 0 -7 Q 2 -14 6 -14 Q 4 -9 5 -7 Z"/>
<circle cx="8" cy="-3" r="1.2" fill="#f7f1e0"/>''',
    "orca-fin": '''<path class="rt-orca" d="M -2.2 3 Q -1.8 -1 0 -2.8 Q 0.2 0 2 3 Z"/>
<path class="rt-water-deco" d="M -5 4.5 q 2.5 -2.5 5 0 q 2.5 2.5 5 0"/>''',
    "humpback": '''<path fill="#5b7f95" d="M -17 -1 Q -15 -6.5 -6 -7.8 Q 4 -9 10 -4.5 Q 13 -2 12.5 0.5 L 12 1.5 Q 4 4.2 -8 4 Q -16 3.8 -17.5 2 Q -18.2 0.5 -17 -1 Z"/>
<path fill="#5b7f95" d="M 1.5 -8.2 Q 3.5 -11 6 -10.2 Q 4.8 -8.8 5 -7.6 Z"/>
<path fill="#5b7f95" d="M 11.5 0.5 Q 15 -1.5 16.5 -5.5 Q 17.5 -2.5 20 -0.5 Q 16.5 1 14 3.5 Q 12.5 2 11.5 0.5 Z"/>
<circle cx="-13.5" cy="-1.5" r="1.2" fill="#f7f1e0"/>
<path class="rt-water-deco" d="M -11 -6.6 L -11 -10.5 M -11 -10.5 Q -12.5 -13 -14.5 -14 M -11 -10.5 Q -11 -13.5 -11 -15.5 M -11 -10.5 Q -9.5 -13 -7.5 -14"/>''',
    "gulls": '''<g class="rt-doodle" fill="none" stroke-width="1.2">
<path d="M -8 -6 Q -6 -9 -4 -6 Q -2 -9 0 -6"/>
<path d="M 6 4 Q 8 1 10 4 Q 12 1 14 4"/></g>''',
}
# Two the hand-drawn chart never needed, in its own hand: thin stroke, the
# same cream fill. They live here rather than in panel 2's defs because
# INLINE_GLYPHS is exactly the place for a glyph panel 2 does not carry.
INLINE_GLYPHS["city"] = '<g class="rt-doodle" stroke-width="1.1">\n<path fill="#f7f1e0" d="M -13 8 L -13 -4 L -8 -4 L -8 8 Z"/>\n<path fill="#f7f1e0" d="M -6 8 L -6 -12 L -1 -12 L -1 8 Z"/>\n<path fill="#f7f1e0" d="M 1 8 L 1 -7 L 6 -7 L 6 8 Z"/>\n<path fill="#f7f1e0" d="M 8 8 L 8 -16 L 12 -16 L 12 8 Z"/>\n<path fill="none" stroke-width="0.7" d="M -11 -1 h 1 M -11 3 h 1 M -4 -9 h 1 M -4 -5 h 1 M -4 -1 h 1 M 3 -4 h 1 M 3 0 h 1 M 10 -13 v 2 M 10 -8 v 2"/>\n<path fill="none" d="M -15 8 H 14"/></g>'
INLINE_GLYPHS["plane"] = '<g class="rt-doodle" stroke-width="1.1">\n<path fill="#f7f1e0" d="M -14 1 L 4 -1 L 12 0 L 12 2 L 4 3 L -14 3 Z"/>\n<path fill="#f7f1e0" d="M -4 0 L 2 -11 L 5 -11 L 1 0 Z"/>\n<path fill="#f7f1e0" d="M -4 3 L 2 13 L 5 13 L 1 3 Z"/>\n<path fill="#f7f1e0" d="M 8 0 L 11 -5 L 13 -5 L 11 1 Z"/></g>'
INLINE_GLYPHS["glacier_peak"] = INLINE_GLYPHS["cone"]
INLINE_GLYPHS["rainier"] = INLINE_GLYPHS["cone"]
INLINE_GLYPHS["orca-pod"] = INLINE_GLYPHS["orca"] + '''
<path class="rt-orca" d="M 26 3 Q 27.5 -3 31 -4 Q 29.5 -0.5 30.5 3 Z"/>
<path class="rt-orca" d="M -25 4 Q -24 -0.5 -21.5 -1.5 Q -22.5 1 -21.5 4 Z"/>
<g class="rt-water-deco"><path d="M 20 6 q 4 -4 8 0 q 4 4 8 0"/>
<path d="M -29 7 q 3.5 -3.5 7 0"/></g>'''


def panel2_defs(html: str) -> str:
    """Lift panel 2's glyph defs and re-emit them under an sg- prefix."""
    start = html.index('aria-label="Illustrated chart of Salish Sea routes')
    d0 = html.index("<defs>", start) + len("<defs>")
    d1 = html.index("</defs>", d0)
    defs = html[d0:d1]
    defs = re.sub(r'<clipPath id="rt-frame-clip">.*?</clipPath>', "", defs, flags=re.S)
    # The comments in panel 2's defs explain panel 2. Lifting them too would
    # duplicate a page of prose into the generated markup.
    defs = re.sub(r"<!--.*?-->", "", defs, flags=re.S)
    defs = re.sub(r"\s{2,}", " ", defs)
    defs = defs.replace('id="ic-', 'id="sg-').replace('href="#ic-', 'href="#sg-')
    defs = defs.replace('id="rt-track-arrow"', 'id="sg-track-arrow"')
    defs = defs.replace("url(#rt-track-arrow)", "url(#sg-track-arrow)")
    extra = "".join(f'<g id="sg-{k}">{v}</g>' for k, v in INLINE_GLYPHS.items())
    return defs + extra


def glyph_extents(defs: str) -> dict[str, tuple[float, float]]:
    """How big each doodle actually is, read off its own path data.

    The cluster arithmetic depends on this: a 44-unit whale covers 12 km of
    ground on this sheet and an 11-unit anchor covers 3, so guessing one size
    for all of them would either scatter the map or crowd it.
    """
    out: dict[str, tuple[float, float]] = {}
    for m in re.finditer(r'<g id="sg-([a-z_-]+)"[^>]*>(.*?)(?=<g id="sg-|<clipPath|$)',
                         defs, re.S):
        name, body = m.group(1), m.group(2)
        xs: list[float] = []
        ys: list[float] = []
        for d in re.findall(r'\sd="([^"]+)"', body):
            nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", d)]
            xs += nums[0::2]
            ys += nums[1::2]
        for c in re.finditer(r"<circle([^>]*)/>", body):
            a = c.group(1)
            cx = float(re.search(r'cx="(-?[\d.]+)"', a).group(1)) if "cx=" in a else 0.0
            cy = float(re.search(r'cy="(-?[\d.]+)"', a).group(1)) if "cy=" in a else 0.0
            r = float(re.search(r'\br="(-?[\d.]+)"', a).group(1)) if " r=" in a else 0.0
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        if xs and ys:
            out[name] = (max(xs) - min(xs), max(ys) - min(ys))
    return out


# ------------------------------------------------------------------ geo layers

DRAWN_RIVERS = {
    "Nooksack River", "Skagit River", "Skykomish River", "Snoqualmie River",
    "Green River", "Elwha River", "Dosewallips River", "Skokomish River",
    "Chehalis River", "Sammamish River", "Duwamish River", "Cedar River",
    "Hoh River", "Quinault River", "Snohomish River", "Puyallup River",
    "Dungeness River", "Nisqually River", "Baker River", "Sauk River",
    "Deschutes River", "Humptulips River", "Queets River", "Wynoochee River",
    # the Rockies sheet
    "Bow River", "Athabasca River", "North Saskatchewan River",
    "Kicking Horse River", "Columbia River", "Sunwapta River", "Miette River",
}


_LAKES: dict = {}


def load_opt(layer: str) -> list:
    """A layer if it has been fetched, nothing if it has not.

    The Rockies layers are a separate fetch covering a separate part of the world;
    everything is clipped by frame anyway, so loading them alongside the Salish
    ones costs nothing on the sheets that do not reach them.
    """
    try:
        return load(layer)
    except SystemExit:
        return []


def lakes(rect):
    """Lakes in a frame, cached: base_layers asks three times per sheet."""
    if rect in _LAKES:
        return _LAKES[rect]
    w, s, e, n = rect
    out = []
    for el in load("water") + load_opt("rockies_water"):
        b = el.get("bounds")
        if b and (b["maxlat"] < s or b["minlat"] > n or b["maxlon"] < w or b["minlon"] > e):
            continue
        name = el.get("tags", {}).get("name", "")
        if el["type"] == "way":
            rings, inner = [way_coords(el)], []
        else:
            ways = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                    for m in el.get("members", []) if m.get("role") in ("outer", "")]
            rings = [r for r in stitch([x for x in ways if len(x) > 1])
                     if len(r) > 3 and r[0] == r[-1]]
            # Mercer Island is a hole in Lake Washington, not a piece of coast, so
            # it never reaches land_rings. Dropping the inner rings painted the
            # lake straight over the island.
            iways = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                     for m in el.get("members", []) if m.get("role") == "inner"]
            inner = [r for r in stitch([x for x in iways if len(x) > 1])
                     if len(r) > 3 and r[0] == r[-1]]
        out.append((name, [r for r in rings if len(r) > 3], inner))
    _LAKES[rect] = out
    return out


def rivers(rect):
    chains = defaultdict(list)
    for el in load("rivers") + load_opt("rockies_rivers"):
        name = el.get("tags", {}).get("name", "")
        if name not in DRAWN_RIVERS:
            continue
        chains[name].append(way_coords(el))
    out = []
    for name, ways in chains.items():
        for ch in stitch([w for w in ways if len(w) > 1]):
            out += [(name, p) for p in clip_chain(ch, rect)]
    return out


def parks(rect):
    out = []
    for el in load("parks") + load_opt("rockies_parks"):
        name = el.get("tags", {}).get("name", "")
        if name not in ("Olympic National Park", "North Cascades National Park",
                        "Mount Rainier National Park", "Banff National Park",
                        "Jasper National Park", "Yoho National Park",
                        "Kootenay National Park"):
            continue
        ways = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                for m in el.get("members", []) if m.get("role") == "outer"]
        rings = [r for r in stitch([x for x in ways if len(x) > 1]) if len(r) > 3]
        out.append((name, rings))
    return out


# ------------------------------------------------------------------ road graph

class Roads:
    """The highway network, as a graph, so a drive leg can be routed on it."""

    _shared = None

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def __init__(self) -> None:
        self.pos: dict[int, tuple[float, float]] = {}
        self.adj: dict[int, list[tuple[int, float, frozenset]]] = defaultdict(list)
        for el in load("roads") + load("links"):
            nodes, geom = el.get("nodes", []), el.get("geometry", [])
            if len(nodes) != len(geom) or len(nodes) < 2:
                continue
            refs = frozenset(r.strip() for r in
                             el.get("tags", {}).get("ref", "").split(";") if r.strip())
            for nid, p in zip(nodes, geom):
                if p:
                    self.pos[nid] = (p["lon"], p["lat"])
            for a, b in zip(nodes, nodes[1:]):
                if a in self.pos and b in self.pos:
                    d = _dist(self.pos[a], self.pos[b])
                    self.adj[a].append((b, d, refs))
                    self.adj[b].append((a, d, refs))
        self._bridge_gaps()

    def _bridge_gaps(self, span: float = 0.0016) -> None:
        """Sew up the seams in the fetched network.

        A junction is often built of one unnumbered stub, and the fetch only
        asked for ways that carry a route number, so SR-20 on Whidbey arrives
        in two halves that stop twenty metres short of each other. The pieces
        are found by connectivity and the closest pair of ends between two
        pieces is joined, at twentyfold cost, so the router only ever uses a
        seam to cross one.
        """
        parent: dict[int, int] = {n: n for n in self.pos}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for u, edges in self.adj.items():
            for v, _, _ in edges:
                ru, rv = find(u), find(v)
                if ru != rv:
                    parent[ru] = rv

        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for nid, (lon, lat) in self.pos.items():
            buckets[(int(lon / span), int(lat / span))].append(nid)

        cand = []
        for nid, (lon, lat) in self.pos.items():
            bx, by = int(lon / span), int(lat / span)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other in buckets.get((bx + dx, by + dy), ()):
                        if other <= nid or find(other) == find(nid):
                            continue
                        d = _dist(self.pos[nid], self.pos[other])
                        if d < span:
                            cand.append((d, nid, other))
        cand.sort()
        sewn = 0
        for d, a, b in cand:
            if find(a) == find(b):
                continue
            parent[find(a)] = find(b)
            self.adj[a].append((b, d * 20, frozenset()))
            self.adj[b].append((a, d * 20, frozenset()))
            sewn += 1
        print(f"  road graph: {len(self.pos)} nodes, {sewn} seams sewn")

    def nearest(self, lat, lon, refs) -> int:
        best, at, any_best, any_at = 1e9, None, 1e9, None
        for nid, (nlon, nlat) in self.pos.items():
            d = (nlat - lat) ** 2 + ((nlon - lon) * 0.67) ** 2
            if d < any_best:
                any_best, any_at = d, nid
            if d < best and any(r in refs for _, _, rs in self.adj[nid] for r in rs):
                best, at = d, nid
        # Prefer a node carrying one of this leg's route numbers, but only if it
        # is genuinely near: the Anacortes terminal was snapping 8 km inland to
        # the nearest SR-20 node, because the terminal approach carries no number
        # at all. Beyond twice the distance of the closest road, take the closest.
        if at is not None and best <= any_best * 4.0:
            return at
        return any_at

    def route(self, checkpoints, refs) -> list[tuple[float, float]]:
        refs = set(refs)
        nodes = [self.nearest(lat, lon, refs) for lat, lon in checkpoints]
        path: list[tuple[float, float]] = []
        for a, b in zip(nodes, nodes[1:]):
            leg = self._dijkstra(a, b, refs)
            if not leg:
                print(f"    ! no road path between {self.pos[a]} and {self.pos[b]}")
                leg = [self.pos[a], self.pos[b]]
            path += leg if not path else leg[1:]
        return path

    def _dijkstra(self, a, b, refs):
        """Cheapest path, with anything off the named route charged twelvefold."""
        dist = {a: 0.0}
        prev: dict[int, int] = {}
        q = [(0.0, a)]
        while q:
            d, u = heapq.heappop(q)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w, rs in self.adj[u]:
                nd = d + w * (1.0 if rs & refs else 12.0)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(q, (nd, v))
        if b not in dist:
            return []
        out, cur = [], b
        while cur != a:
            out.append(self.pos[cur])
            cur = prev[cur]
        out.append(self.pos[a])
        out.reverse()
        return out


def _dist(p, q) -> float:
    return math.hypot((p[0] - q[0]) * 0.67, p[1] - q[1])


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Ground distance between two (lat, lon) points, in km."""
    return math.hypot((b[0] - a[0]) * 110.9,
                      (b[1] - a[1]) * 111.32 * math.cos(math.radians((a[0] + b[0]) / 2)))


# ---------------------------------------------------------------- drawing bits

def poly(points, proj, cls, eps=0.4, extra="") -> str:
    pts = rdp([proj(lon, lat) for lon, lat in points], eps)
    if len(pts) < 2:
        return ""
    return f'<path class="{cls}" d="{points_d(pts, False)}"{extra}/>'


def text(t, x, y, cls, anchor="middle", rot=0.0, size=None) -> str:
    style = f' style="font-size:{size}px"' if size else ""
    tr = f' transform="rotate({rot:.0f} {x:.1f} {y:.1f})"' if rot else ""
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="{anchor}"{tr}{style}>{t}</text>')


FONT_W = {"rt-label big": 7.8, "rt-label": 6.4, "rt-label water": 6.4,
          "rt-sub": 5.5, "rt-flavor": 5.6, "rt-quest-item": 5.8}
PAD = 3.0


def _extent(t, cls, size=None):
    w = FONT_W.get(cls, 5.6) * len(t)
    if size:
        w *= size / 11.0
    return w, (13.0 if "big" in cls else 11.0)


def _corners(box):
    cx, cy, w, h, rot = box
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = w / 2, h / 2
    return [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)
            for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]


def _hits(b1, b2) -> float:
    """Overlap of two oriented boxes: separating axis test, then rough area.

    Oriented, because half the names on a chart run along a channel. The old
    axis-aligned version thought "Haro Strait" at 68 degrees was a wide flat
    rectangle, so it reserved water it was not using and let a humpback sit on
    the one place it was.
    """
    p1, p2 = _corners(b1), _corners(b2)
    for poly in (p1, p2):
        for i in range(4):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % 4]
            ax, ay = -(y2 - y1), x2 - x1
            r1 = [ax * x + ay * y for x, y in p1]
            r2 = [ax * x + ay * y for x, y in p2]
            if max(r1) <= min(r2) or max(r2) <= min(r1):
                return 0.0
    xs1 = [p[0] for p in p1]; ys1 = [p[1] for p in p1]
    xs2 = [p[0] for p in p2]; ys2 = [p[1] for p in p2]
    w = min(max(xs1), max(xs2)) - max(min(xs1), min(xs2))
    h = min(max(ys1), max(ys2)) - max(min(ys1), min(ys2))
    return max(w, 0.0) * max(h, 0.0)


class Placer:
    """Keeps what is already on the sheet, and finds room for the next thing.

    Everything it holds is an oriented box: doodles at the size read off their
    own paths, badges, the apron, and the names already placed. A name is
    offered its intended position first, then a ring of alternatives, and takes
    the first that lands on nothing. A name that runs along a channel is offered
    slides up and down that channel instead, which is how a chart moves one.
    """

    def __init__(self) -> None:
        self.taken: list[tuple] = []

    def block(self, box) -> None:
        self.taken.append(box)

    def blocks(self, x, y, w, h, rot=0.0) -> None:
        self.taken.append((x, y, w, h, rot))

    def rect(self, x0, y0, x1, y1) -> None:
        self.taken.append(((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0.0))

    def free(self, box) -> bool:
        return self.overlap(box) <= 4.0

    def overlap(self, box) -> float:
        return sum(_hits(box, other) for other in self.taken)

    @staticmethod
    def text_box(x, y, dx, dy, w, h, anchor, rot):
        """The box a run of text occupies, rotated about its own anchor point."""
        ax, ay = x + dx, y + dy
        off = {"start": w / 2, "end": -w / 2, "middle": 0.0}[anchor]
        cx, cy = ax + off, ay - h / 2 + 2
        if rot:
            a = math.radians(rot)
            ox, oy = cx - ax, cy - ay
            cx = ax + ox * math.cos(a) - oy * math.sin(a)
            cy = ay + ox * math.sin(a) + oy * math.cos(a)
        return (cx, cy, w + PAD * 2, h + PAD * 2, rot)

    def place(self, lines, x, y, cls, anchor, dx, dy, rot=0.0, size=None):
        """Return (dx, dy, anchor) for a block of lines, and reserve the room."""
        w = max(_extent(t, cls, size)[0] for t in lines)
        h = _extent(lines[0], cls, size)[1] * len(lines)
        cands = [(dx, dy, anchor)]
        if rot:
            # slide along the line the name follows, then step off it
            a = math.radians(rot)
            ux, uy = math.cos(a), math.sin(a)
            # A short step off the line beats a long slide along it: an island
            # name that slides 11 km is off its island, but one that steps 3 km
            # sideways is in the water beside it, which is where charts put it.
            for along in (10, -10, 20, -20):
                cands.append((dx + ux * along, dy + uy * along, anchor))
            for across in (11, -11, 18, -18):
                cands.append((dx - uy * across, dy + ux * across, anchor))
            for along in (32, -32, 46, -46):
                cands.append((dx + ux * along, dy + uy * along, anchor))
            # Sideways is capped hard: a water name that steps 8 km off its
            # own channel lands in someone else's, which is how "L. Washington"
            # ended up in West Seattle.
            for across in (24, -24):
                cands.append((dx - uy * across, dy + ux * across, anchor))
                for along in (16, -16, 34, -34):
                    cands.append((dx + ux * along - uy * across,
                                  dy + uy * along + ux * across, anchor))
        else:
            r = min(max(abs(dx), abs(dy), 12), 30)
            for mult in (1.0, 1.35, 1.7, 2.1, 2.6):
                for cdx, cdy, ca in ((r, 4, "start"), (-r, 4, "end"),
                                     (0, -r, "middle"), (0, r + h - 4, "middle"),
                                     (r * 0.8, -r * 0.7, "start"),
                                     (-r * 0.8, -r * 0.7, "end"),
                                     (r * 0.8, r * 0.7, "start"),
                                     (-r * 0.8, r * 0.7, "end")):
                    cands.append((cdx * mult, cdy * mult, ca))
        for cdx, cdy, ca in cands:
            box = self.text_box(x, y, cdx, cdy, w, h, ca, rot)
            if self.free(box):
                self.block(box)
                return cdx, cdy, ca
        best = min(cands, key=lambda c: self.overlap(
            self.text_box(x, y, c[0], c[1], w, h, c[2], rot)))
        self.block(self.text_box(x, y, best[0], best[1], w, h, best[2], rot))
        return best


def leader(x, y, lx, ly, anchor) -> str:
    edge = {"start": -4, "end": 4, "middle": 0}[anchor]
    return (f'<path class="rt-leader" d="M {num(x)} {num(y)} '
            f'{num(lx + edge)} {num(ly - 3)}"/>')


def grid_step(span: float) -> tuple[float, float]:
    """Graticule interval, and the interval that gets a printed number.

    A half degree is right for the whole Salish Sea and useless on a 0.26°
    frame, where it draws one line and labels nothing.
    """
    for step, label in ((0.5, 1.0), (0.25, 0.5), (0.1, 0.5), (0.05, 0.1)):
        if span / step >= 3:
            return step, label
    return 0.02, 0.1


def _tick_label(v: float, step: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".") if step < 0.1 else f"{v:g}"


def grid_ticks(proj: Proj, rect):
    """The graticule's printed numbers: (text, x, y, anchor).

    Shared with the name placer. They were drawn but never registered, which is
    how 48.5°N ended up under Haro Strait.
    """
    w, s, e, n = rect
    _, lstep = grid_step(min(e - w, n - s))
    bx, by, bw, bh = proj.box
    out = []
    lon = math.ceil(w / lstep) * lstep
    while lon <= e:
        x, y = proj(lon, n)
        # A tick on the frame's own edge puts half its label on the apron, which
        # is drawn last and cuts it in two.
        if x - 18 >= bx and x + 18 <= bx + bw:
            out.append((f"{_tick_label(abs(lon), lstep)}°W", x, y + 12, "middle"))
        lon += lstep
    lat = math.ceil(s / lstep) * lstep
    while lat <= n:
        x, y = proj(w, lat)
        out.append((f"{_tick_label(lat, lstep)}°N", x + 5, y - 4, "start"))
        lat += lstep
    return out


def graticule(proj: Proj, rect) -> str:
    """A real graticule, at whatever interval the frame can carry."""
    w, s, e, n = rect
    step, _ = grid_step(min(e - w, n - s))
    lines = []
    lon = math.ceil(w / step) * step
    while lon <= e:
        x0, y0 = proj(lon, s)
        x1, y1 = proj(lon, n)
        lines.append(f"M {num(x0)} {num(y0)} {num(x1)} {num(y1)}")
        lon += step
    lat = math.ceil(s / step) * step
    while lat <= n:
        x0, y0 = proj(w, lat)
        x1, y1 = proj(e, lat)
        lines.append(f"M {num(x0)} {num(y0)} {num(x1)} {num(y1)}")
        lat += step
    out = [f'<g class="rt-grid" opacity="0.7"><path d="{" ".join(lines)}"/></g>']
    for t, x, y, anchor in grid_ticks(proj, rect):
        out.append(text(t, x, y, "rt-flavor", anchor, size=8.5))
    return "".join(out)


def scale_bar(x, y, proj: Proj, max_w: float = 200.0):
    """A three-block bar, and how wide it ended up. Returns (markup, width).

    Three blocks of 10 km is 930 units wide on the Seattle sheet, which is most
    of the map, so the step has to come from the scale. It also has to be capped:
    aiming for a comfortable 230 units made the bar 255 wide on the index sheet
    and it ran straight through the compass, which was sitting at a fixed x.
    """
    k = proj.px_per_km()
    fits = [c for c in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50) if c * k * 3 <= max_w]
    step = max(fits) if fits else 0.1
    out = [f'<g transform="translate({x} {y})">']
    for i in range(3):
        out.append(f'<rect x="{i * step * k:.1f}" y="0" width="{step * k:.1f}" '
                   f'height="4" fill="{"#5a6650" if i % 2 == 0 else "#eef2ea"}" '
                   f'stroke="#5a6650" stroke-width="0.8"/>')
    metres = step < 1
    for i in (0, 1, 2, 3):
        v = i * step
        out.append(text(f"{v * 1000:g}" if metres else f"{v:g}",
                        i * step * k, -4, "rt-sub", "middle", size=9))
    out.append(text("m" if metres else "km", 3 * step * k + 12, 4,
                    "rt-sub", "start", size=9))
    out.append("</g>")
    return "".join(out), 3 * step * k + 34


def compass(x, y) -> str:
    return (f'<g class="rt-compass" transform="translate({x} {y})">'
            '<circle r="26" fill="none" stroke-width="1"/><circle r="2.5"/>'
            '<path d="M 0 -22 L 4 0 L 0 22 L -4 0 Z" fill-opacity="0.85"/>'
            '<path d="M -22 0 L 0 4 L 22 0 L 0 -4 Z" fill-opacity="0.45"/>'
            '<text x="0" y="-31" text-anchor="middle">N</text></g>')


# --------------------------------------------------------------------- content

def visited_split(land):
    """Split land rings into the ones I have set foot on and the ones I have not.

    Decided by containment, so the answer does not depend on the frame: the same
    island must be the same colour on every sheet. Bainbridge came out faded on
    one panel and full on another because the previous rule matched a ring to a
    reference point by *proximity*, and Blake Island's point is five km off
    Bainbridge's south tip.

    An island is not mine if one of `P.UNVISITED_ISLANDS` lies inside it. A rock
    too small to have a name is not mine either. Everything else - the mainland,
    Whidbey, Fidalgo, Vancouver Island - is, which also avoids ever testing the
    frame-closed mainland ring, whose outline can self-intersect and answers
    point-in-polygon wrongly.
    """
    mine, theirs = [], []
    for ring in land:
        # Visited wins. A wider frame merged Whidbey's ring with Camano's, and
        # testing "not visited" first faded the whole of Whidbey with it. The
        # wash boxes fade the unvisited island inside a merged ring by geography,
        # which is the only thing that works once rings can merge.
        if any(in_ring((lo, la), ring) for la, lo in P.VISITED_LAND):
            mine.append(ring)
        elif any(in_ring((lo, la), ring) for la, lo in P.UNVISITED_ISLANDS):
            theirs.append(ring)
        elif ring_span_km(ring) < P.ROCK_SPAN_KM:
            theirs.append(ring)
        else:
            mine.append(ring)
    return mine, theirs


def _near_any(ring, points, km_limit) -> bool:
    """Is any of these (lat, lon) points within km_limit of the ring's outline?"""
    step = max(1, len(ring) // 400)
    for la, lo in points:
        k = math.cos(math.radians(la))
        lim = km_limit * km_limit
        for i in range(0, len(ring), step):
            x, y = ring[i]
            dx = (x - lo) * 111.32 * k
            dy = (y - la) * 110.9
            if dx * dx + dy * dy < lim:
                return True
    return False


def ring_span_km(ring) -> float:
    """The diagonal of a ring's bounding box, in km.

    Used instead of the shoelace area because the frame closes the mainland
    coastline into a ring that self-intersects, and the shoelace of that ring
    very nearly cancels to zero: the whole of Washington was being classified as
    an unnamed rock and drawn half transparent.
    """
    if len(ring) < 3:
        return 0.0
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    lat0 = (min(ys) + max(ys)) / 2
    dx = (max(xs) - min(xs)) * 111.32 * math.cos(math.radians(lat0))
    dy = (max(ys) - min(ys)) * 110.9
    return math.hypot(dx, dy)


def ring_km2(ring) -> float:
    """Rough area of a lon/lat ring in square km."""
    if len(ring) < 3:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    k = math.cos(math.radians(lat0))
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        a += (x1 * k * 111.32) * (y2 * 110.9) - (x2 * k * 111.32) * (y1 * 110.9)
    return abs(a) / 2


def base_layers(proj: Proj, rect, eps: float, out: list[str]) -> None:
    land, holes = land_rings(rect)
    d = path_d(land, proj, eps)
    # The glow is an 8px stroke at a third opacity: it can be a much coarser
    # version of the same coast, and drawing it coarse halves the file. Nine
    # times the tolerance is still well under the stroke's own width, so there is
    # nothing in it to see; on the San Juans the halo alone was 16 KB.
    out.append(f'<path class="rt-coast-glow" d="{path_d(land, proj, eps * 9)}"/>')
    mine, theirs = visited_split(land)
    # The region wash is about the mainland. Bainbridge sits inside the Kitsap
    # polygon and is not part of the Kitsap: an island I have been to must keep
    # its colour whatever the wash says about the peninsula beside it.
    # Island-sized only. The frame closing can merge an island's ring with the
    # mainland it sits beside, and redrawing such a ring over the wash un-fades
    # the peninsula with it: that is how Gig Harbor kept its colour.
    isles = [r for r in mine
             if ring_span_km(r) < 60
             and any(in_ring((lo, la), r) for la, lo in P.ISLANDS_VISITED)]
    main = [r for r in mine if r not in isles]
    dm = path_d(main, proj, eps)
    di = path_d(isles, proj, eps)
    dt = path_d(theirs, proj, eps)
    # The mainland is one ring and not one experience. Inside the unvisited
    # regions its land is washed back; a POI standing there keeps its own colour.
    rings = []
    for r in P.UNVISITED_REGIONS:
        pts = [proj(lo, la) for la, lo in r["ring"]]
        rings.append(points_d(rdp(pts, 0.5), True))
    for _n, s0, w0, n0, e0 in P.UNVISITED_ISLAND_BOXES:
        pts = [proj(w0, n0), proj(e0, n0), proj(e0, s0), proj(w0, s0)]
        rings.append(points_d(pts, True))
    uid0 = f"{abs(hash((rect, 'land'))) % 999983}"
    if dm:
        out.append(f'<path id="sg-lm-{uid0}" class="rt-island" d="{dm}"/>')
    if di:
        out.append(f'<path id="sg-li-{uid0}" class="rt-island" d="{di}"/>')
    if dt:
        out.append(f'<g class="rt-unvisited">'
                   f'<path id="sg-lt-{uid0}" class="rt-island" d="{dt}"/></g>')

    for name, park_rings in parks(rect):
        pd = path_d([r for r in (clip_ring(ring, rect) for ring in park_rings) if r],
                    proj, max(eps, 1.6))
        if pd:
            out.append(f'<path d="{pd}" fill="#7d8f5c" fill-opacity="0.12" '
                       f'stroke="#6f7e4a" stroke-width="1" stroke-dasharray="5 4" '
                       f'opacity="0.55"/>')
    for name, chain in rivers(rect):
        out.append(poly(chain, proj, "rt-river", max(eps, 1.0),
                        ' stroke-width="2.2" opacity="0.7"'))

    lake_d = [path_d([r for r in (clip_ring(ring, rect) for ring in rings2) if r],
                     proj, eps) for _, rings2, _inner in lakes(rect)]
    lake_d = [x for x in lake_d if x]
    if lake_d:
        out.append(f'<path class="rt-lake" d="{" ".join(lake_d)}"/>')
    isl = [path_d([r for r in (clip_ring(ring, rect) for ring in inner) if r],
                  proj, eps) for _, _rings, inner in lakes(rect) if inner]
    isl = [x for x in isl if x]
    if isl:
        out.append(f'<path class="rt-island" d="{" ".join(isl)}"/>')


    if rings:
        # Painted last of all, over every land layer including the islands that
        # lakes hold, in the water colour at half strength: invisible where it
        # covers water, fading where it covers land. One path element per region,
        # because fourteen subpaths in one element cancel wherever two overlap
        # under the default nonzero fill rule, and Gig Harbor sits in two of them.
        # Clipped to the land. Painting the regions straight onto the sheet drew
        # them as visible rectangles: over open water the wash colour is the water
        # colour and should vanish, but it also fell across the coast glow and the
        # graticule and their edges showed. Clipping to the land means only land
        # is ever touched, and the region's own shape never appears.
        # The clip points at the land paths by id rather than repeating their
        # geometry: a second copy of every coastline added 60 KB a sheet.
        uses = "".join(f'<use href="#sg-{k}-{uid0}"/>'
                       for k, d in (("lm", dm), ("li", di), ("lt", dt)) if d)
        uid3 = f"{abs(hash((rect, 'landclip'))) % 999983}"
        if uses:
            out.append(f'<clipPath id="sg-land-{uid3}">{uses}</clipPath>')
            blur = max(3.0, 26.0 / max(proj.px_per_km(), 1.0))
            out.append(f'<filter id="sg-soft-{uid3}" x="-8%" y="-8%" '
                       f'width="116%" height="116%">'
                       f'<feGaussianBlur stdDeviation="{blur:.1f}"/></filter>')
            out.append(f'<g clip-path="url(#sg-land-{uid3})" '
                       f'filter="url(#sg-soft-{uid3})">')
            for ring_d in rings:
                out.append(f'<path d="{ring_d}" fill="{WATER_FILL}" '
                           f'fill-opacity="0.62" stroke="none"/>')
            out.append("</g>")
        # Punch the visited spots back through: Poulsbo is mine and the Kitsap is
        # not, Victoria is mine and Vancouver Island is not. This is the whole
        # point of washing by region rather than by landmass.
        bx2, by2, bw2, bh2 = proj.box
        spots = []
        for _nm, la, lo, km_r in P.VISITED_SPOTS:
            cx, cy = proj(lo, la)
            r = km_r * proj.px_per_km()
            if (cx + r < bx2 or cx - r > bx2 + bw2
                    or cy + r < by2 or cy - r > by2 + bh2):
                continue
            spots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}"/>')
        if spots and (dm or di):
            uid2 = f"{abs(hash((rect, 'spot'))) % 999983}"
            out.append(f'<clipPath id="sg-spot-{uid2}">{"".join(spots)}</clipPath>')
            out.append(f'<g clip-path="url(#sg-spot-{uid2})">'
                       + "".join(f'<use href="#sg-{k}-{uid0}" class="rt-island"/>'
                                 for k, d in (("lm", dm), ("li", di)) if d)
                       + '</g>')

    # Diablo Lake keeps the colour panel 2 gave it: rock-flour turquoise.
    for name, rings, _inner in lakes(rect):
        if name in ("Diablo Lake", "Gorge Lake", "Lake Louise", "Moraine Lake",
                    "Bow Lake", "Peyto Lake", "Emerald Lake", "Maligne Lake",
                    "Lake Minnewanka", "Hector Lake", "Medicine Lake"):
            dd = path_d([r for r in (clip_ring(ring, rect) for ring in rings) if r],
                        proj, eps)
            if dd:
                out.append(f'<path d="{dd}" fill="#79bdb2" stroke="#4f8f86" '
                           f'stroke-width="1.1" stroke-linejoin="round"/>')


def crest_markup(proj: Proj, frame=None) -> str:
    """The divide, hachured the old way: ticks down the steep east side."""
    chain = [(lon, lat) for lat, lon in P.CREST]
    pieces = clip_chain(chain, grow(frame)) if frame is not None else [chain]
    hach, spine = [], []
    step = 9.0
    for piece in pieces:
        if len(piece) < 2:
            continue
        pts = [proj(lon, lat) for lon, lat in piece]
        spine.append(points_d(pts, False))
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            seg = math.hypot(x2 - x1, y2 - y1)
            if seg < 1e-6:
                continue
            n = max(1, int(seg // step))
            for i in range(n):
                t = i / n
                x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                nx, ny = (y2 - y1) / seg, -(x2 - x1) / seg
                s = -1 if nx < 0 else 1
                hach.append(f"M {num(x)} {num(y)} "
                            f"{num(x + nx * s * 7)} {num(y + ny * s * 7)}")
    if not spine:
        return ""
    return (f'<path fill="none" stroke="#6f7e4a" stroke-width="1.1" '
            f'stroke-linecap="round" opacity="0.75" d="{" ".join(hach)}"/>'
            f'<path fill="none" stroke="#5d6b3f" stroke-width="2" '
            f'stroke-linecap="round" d="{" ".join(spine)}"/>')



def glyph_box(p: dict, sizes: dict, drawn: bool = True,
              sheet_scale: float = 1.0) -> tuple[float, float]:
    """The room a place needs on a sheet: its glyph, plus a hair of air.

    A place the sheet draws as a plain dot needs a dot's worth. Sizing dots by
    the glyph they are not drawing is what made the index sheet nudge seventeen
    of them off their own coordinates.
    """
    if not p.get("ic") or not drawn:
        return (9.0, 9.0)
    w, h = sizes.get(p["ic"], (24.0, 24.0))
    s = abs(p.get("scale", 1.0)) * sheet_scale
    return (max(w * s, 12) + 3, max(h * s, 12) + 3)


# How far a glyph may be nudged off its own place: never further than the gap it
# is resolving, so the nudge cannot invert "this is next to that". Two shops 60 m
# apart therefore get no nudge at all, and wait for the sheet where they fit.
NUDGE_MAX, NUDGE_MIN, NUDGE_SHARE = 26.0, 8.0, 0.9

# Which side of the shore a drawing belongs on. A beach, a marina and a
# waterfront park all have coordinates on the waterline, and a 20-unit glyph
# anchored on the waterline reads as floating: Alki's Statue of Liberty was
# standing in Puget Sound and Meydenbauer's sailboat was parked on the lawn.
WATER_SIDE = {"santana", "orca", "orca-pod", "orca-fin", "humpback", "ship",
              "duck", "gulls", "salmon", "oyster", "swimraft"}
NEUTRAL_SIDE = {"anchor"}          # a ferry slip is the waterline, either side reads


def glyph_side(ic):
    """True for dry land, False for water, None for don't care."""
    if not ic or ic in NEUTRAL_SIDE:
        return None
    return ic not in WATER_SIDE


_SNAP: dict = {}


def draw_at(lat, lon, ic):
    """Where a glyph is actually drawn: its own position, put on the right side.

    Capped at 500 m and cached, because it is a property of the place and the
    coastline, not of the sheet. The move is reported by `audit_sides` so it can
    be checked rather than trusted.
    """
    want = glyph_side(ic)
    if want is None:
        return (lat, lon), 0.0
    key = (round(lat, 6), round(lon, 6), want)
    if key not in _SNAP:
        (lo, la), moved = snap_to((lon, lat), want, 500.0)
        _SNAP[key] = ((la, lo), moved)
    return _SNAP[key]


def poi_xy(p, proj: Proj):
    """The projected point a place's glyph is drawn at."""
    (lat, lon), _ = draw_at(p["at"][0], p["at"][1], p.get("ic"))
    return proj(lon, lat)


def in_country_of(lat, lon, usa_only=True) -> bool:
    """May a drawing stand here? Every sheet but the Vancouver one says the
    United States only: the geography and the names cross the treaty line, the
    drawings do not."""
    return P.in_usa(lat, lon) if usa_only else True


def is_quiet(p: dict, sheet_key) -> bool:
    """Does this sheet print this place's name, or leave it to hover?"""
    return sheet_key in p.get("quiet_on", ())


def fit_places(places, proj: Proj, sizes: dict, sheet_key=None, draws=True,
               sheet_scale=1.0):
    """Draw a doodle on every place the sheet can hold, in three passes.

    One: a doodle at the true position for everything with room, priority to the
    places panel 2 gives a printed name to. Two: a short nudge onto free paper
    for the leftovers, each on a leader back to a dot on the real spot. Three:
    whatever still cannot fit stays a plain dot with its hover name, and gets its
    doodle on the sheet one rung up the ladder.
    """
    placer = Placer()
    anchors, displaced, dots = [], [], []
    if not draws:
        # An index sheet draws every place as a 2-unit dot. A dot's whole job is
        # to sit on the true position, so it is never nudged; two dots 500 m
        # apart may touch, and that is the honest picture.
        for p in places:
            x, y = poi_xy(p, proj)
            placer.blocks(x, y, 9.0, 9.0)
        return list(places), [], [], placer
    # Printed names first, then doodles, then the plain chart stops. A stop with
    # no glyph reserving paper ahead of a doodle is how Cascade Falls lost its
    # waterfall to the 9-unit dot marking the trail 200 m away.
    order = sorted(places, key=lambda p: (
        0 if p["label"][0] == "text" and not is_quiet(p, sheet_key) else 1,
        0 if p.get("ic") else 1))
    leftover = []
    for p in order:
        x, y = poi_xy(p, proj)
        w, h = glyph_box(p, sizes, draws and P.in_usa(*p["at"]), sheet_scale)
        box = (x, y, w, h, 0.0)
        if placer.free(box):
            placer.block(box)
            anchors.append(p)
        else:
            leftover.append(p)
    for p in leftover:
        x, y = poi_xy(p, proj)
        w, h = glyph_box(p, sizes, draws and P.in_usa(*p["at"]), sheet_scale)
        # A nudge used to be capped at nine tenths of the gap it was resolving,
        # so two places 60 m apart got no nudge at all and one of them lost its
        # doodle to a town plan. With a leader line back to a dot on the true
        # spot the displacement is stated on the sheet, so it can be as long as
        # the paper needs: this is what a printed chart does with a leader.
        cap = NUDGE_MAX
        spot = None
        want = glyph_side(p.get("ic"))
        for strict in (True, False):
            for r in (cap * 0.45, cap * 0.7, cap):
                for i in range(8):
                    a = math.pi / 4 * i
                    dx, dy = r * math.cos(a), r * math.sin(a)
                    box = (x + dx, y + dy, w, h, 0.0)
                    if not placer.free(box):
                        continue
                    # A nudge of 26 units is 840 m on the Seattle sheet, which is
                    # enough to walk Alki's statue back into Puget Sound. The
                    # first pass only accepts spots on the right side of the
                    # shore; the second gives up on that rather than lose the
                    # drawing.
                    if strict and want is not None:
                        la2, lo2 = proj.inverse(x + dx, y + dy)
                        if is_dry((lo2, la2)) != want:
                            continue
                    spot = (dx, dy, box)
                    break
                if spot:
                    break
            if spot:
                break
        if spot:
            placer.block(spot[2])
            displaced.append((p, spot[0], spot[1]))
        else:
            dots.append(p)
    return anchors, displaced, dots, placer


def fit_doodles(items, proj: Proj, sizes: dict, placer: Placer):
    """Place the scenery so it does not sit on the places.

    The ducks were on the camp tent and the hen on the pottery because the
    decorative doodles were drawn straight from their coordinates and never
    offered to the placer at all. They are scenery, so a few units of nudge
    costs nothing.
    """
    out = []
    for ic, lat, lon, sc in items:
        x, y = proj(lon, lat)
        w, h = sizes.get(ic, (24.0, 24.0))
        w, h = max(w * abs(sc), 10), max(h * abs(sc), 10)
        if placer.free((x, y, w, h, 0.0)):
            placer.block((x, y, w, h, 0.0))
            out.append((ic, x, y, sc))
            continue
        spot = None
        for r in (12, 18, 26, 36, 48):
            for i in range(8):
                a = math.pi / 4 * i
                nx, ny = x + r * math.cos(a), y + r * math.sin(a)
                if placer.free((nx, ny, w, h, 0.0)):
                    spot = (nx, ny)
                    break
            if spot:
                break
        if spot:
            placer.block((spot[0], spot[1], w, h, 0.0))
            out.append((ic, spot[0], spot[1], sc))
        else:
            placer.block((x, y, w, h, 0.0))
            out.append((ic, x, y, sc))
    return out


def poi_group(p: dict, proj: Proj, at=None, scale=1.0, dot_only=False,
              quiet=False, named=False, hover_at=None) -> str:
    """The glyph itself, hoverable, with the hover name panel 2 gives it.

    `quiet` keeps the doodle and drops the printed name to hover only. Three
    ferry slips 2 km apart need it: on the Seattle sheet their names fit, and on
    the overview the same three names are one word of ink.
    """
    x, y = at if at else poi_xy(p, proj)
    sc = p.get("scale", 1.0) * scale
    body = []
    if p.get("ic") and not dot_only:
        tr = f' transform="scale({sc:.2f})"' if abs(sc - 1) > 0.01 else ""
        if sc < 0:
            tr = f' transform="scale({sc:.2f}, {abs(sc):.2f})"'
        body.append(f'<use href="#sg-{p["ic"]}"{tr}/>')
    else:
        r = 2.2 if dot_only else p.get("stop_r", 3.5) * scale
        body.append(f'<circle class="{"sg-dot" if dot_only else "rt-stop"}" '
                    f'r="{r:.1f}"/>')
    if not dot_only:
        for ic, dx, dy, s in p.get("extra", []):
            body.append(f'<use href="#sg-{ic}" transform="translate({dx * scale:.1f}, '
                        f'{dy * scale:.1f}) scale({s * scale:.2f})"/>')
    body.append(f'<circle class="rt-hit" r="{(9 if dot_only else p.get("hit", 13)) * 1:.0f}"/>')
    kind, dx, dy, anchor, cls, lines = p["label"]
    # `named` means the sheet already prints this name beside the drawing, so
    # repeating it on hover puts a second copy of the same words on top of the
    # first: fifteen of them on the Seattle sheet alone.
    if (kind == "hover" or dot_only or quiet) and not named:
        if hover_at is not None:
            lx, ly, la = hover_at
        elif kind == "hover" or (quiet and not dot_only):
            lx, ly, la = dx, dy, anchor
        else:
            lx, ly, la = 11, 4, "start"
        for i, line in enumerate(lines):
            body.append(f'<text class="rt-poi-label" x="{lx}" y="{ly + i * 12}" '
                        f'text-anchor="{la}">{line}</text>')
    g = (f'<g class="rt-poi" data-name="{p["name"]}" '
         f'transform="translate({x:.1f}, {y:.1f})">{"".join(body)}</g>')
    return f'<g class="rt-unvisited">{g}</g>' if p.get("unvisited") else g


def poi_label(p: dict, proj: Proj, placer: Placer, off=(0.0, 0.0),
              quiet=False, loud=False, subs=True) -> str:
    """The printed name, if this sheet prints one.

    `loud` prints the names panel 2 keeps for hover. A town plan exists to pull
    four shops 70 m apart off each other, and it was spending a whole pane to
    show four anonymous dots: at 420 units per km there is room to say which is
    which.
    """
    kind, dx, dy, anchor, cls, lines = p["label"]
    if quiet or (kind != "text" and not loud):
        return ""
    if kind != "text":
        cls = cls or "rt-sub"
    x, y = poi_xy(p, proj)
    x, y = x + off[0], y + off[1]
    # The index sheet prints the town, not its subtitle: "Skagit Valley" is
    # orientation, "Tulip Festival" is what the Skagit sheet is for.
    sub = p.get("sub") if subs else None
    block = list(lines) + (list(sub[5]) if sub else [])
    dx, dy, anchor = placer.place(block, x, y, cls, anchor, dx, dy)
    out = []
    if math.hypot(dx, dy) > 26:
        out.append(leader(x, y, x + dx, y + dy, anchor))
    for i, line in enumerate(lines):
        out.append(text(line, x + dx, y + dy + i * 13, cls, anchor))
    if sub:
        base = dy + len(lines) * 13 - 1
        for i, line in enumerate(sub[5]):
            out.append(text(line, x + dx, y + base + i * 12, sub[4], anchor))
    body = "".join(out)
    return f'<g class="rt-unvisited">{body}</g>' if p.get("unvisited") else body


def unique_places():
    seen, out = set(), []
    for p in sorted(P.POIS, key=lambda q: 0 if q["label"][0] == "text" else 1):
        if p["at"] in seen:
            continue
        seen.add(p["at"])
        out.append(p)
    return out


# ------------------------------------------------------------------ one sheet

def grow(frame, share: float = 0.04):
    """The frame plus a margin, for clipping line work without visible ends."""
    w, s, e, n = frame
    dx, dy = (e - w) * share, (n - s) * share
    return (w - dx, s - dy, e + dx, n + dy)


def lines_on(chains, proj: Proj, frame, cls, eps=0.4, extra="") -> list[str]:
    """Draw only the pieces of these polylines that reach this sheet.

    The overview can afford to hand the whole of I-5 to the clip path. A 33 km
    sheet cannot: it was carrying every vertex from Blaine to Tacoma to draw
    twelve of them.
    """
    box = grow(frame)
    out = []
    for chain in chains:
        for piece in clip_chain(list(chain), box):
            d = poly(piece, proj, cls, eps, extra)
            if d:
                out.append(d)
    return out


LAND_FILL, WATER_FILL = "#8d9b63", "#eef2ea"


def base_fill(frame) -> str:
    """What colour the paper starts as.

    Land is painted over water, so water is the right default wherever a coast
    ring will arrive to cover the land. A frame with no coastline in it at all
    gets no such ring, and then the default decides the whole pane: Meydenbauer
    Bay is 8 km from salt water, so Bellevue was drawn as open sea.
    """
    land, holes = land_rings(frame)
    if land or holes:
        return WATER_FILL
    w, s, e, n = frame
    return LAND_FILL if on_land(((w + e) / 2, (s + n) / 2)) else WATER_FILL


FERRY_BOX = (-123.45, 47.45, -122.20, 48.78)
_TRACKS: list = []


def ferry_tracks():
    """Every ferry leg as a track that stays in the water.

    Routed once over a water mask and cached. A straight line from Anacortes to
    Friday Harbor crossed Decatur, Lopez and Shaw.
    """
    if not _TRACKS:
        grid = WaterGrid.shared(FERRY_BOX)
        for leg in P.FERRY_LEGS:
            track = [leg[0]]
            for a, b in zip(leg, leg[1:]):
                track += grid.route(a, b)[1:]
            _TRACKS.append(track)
    return _TRACKS


def draw_frame_content(proj: Proj, frame, out: list[str], sizes: dict,
                       eps: float, furniture: bool):
    """Everything that belongs to a piece of ground, at whatever scale it is."""
    bx, by, bw, bh = proj.box
    out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
               f'fill="{base_fill(frame)}"/>')
    if furniture:
        out.append(graticule(proj, frame))
    base_layers(proj, frame, eps, out)

    if furniture:
        out += lines_on([[(lon, lat) for lat, lon in P.BORDER],
                         [(lon, lat) for lat, lon in P.BORDER_49]],
                        proj, frame, "rt-border")
        if any(on_frame(lat, lon, grow(frame)) for lat, lon in P.CREST):
            out.append(crest_markup(proj, frame))
        roads = Roads.shared()
        out += lines_on([roads.route(leg["via"], leg["refs"]) for leg in P.DRIVE_LEGS],
                        proj, frame, "rt-drive-line", 0.35)
        out += lines_on([[(lon, lat) for lat, lon in d] for d in P.ISLAND_DRIVES],
                        proj, frame, "rt-drive-line", 0.3)
        out += lines_on([[(lon, lat) for lat, lon in t] for t in P.TRAILS],
                        proj, frame, "rt-trail-line", 0.2)
    for leg in ferry_tracks():
        if any(on_frame(lat, lon, frame, -0.02) for lat, lon in leg):
            out.append(poly([(lon, lat) for lat, lon in leg], proj, "rt-ferry-line",
                            0.2, ' marker-start="url(#sg-track-arrow)"'
                                 ' marker-end="url(#sg-track-arrow)"'))
    for name, span in P.BRIDGES:
        if any(on_frame(lat, lon, frame) for lat, lon in span):
            out.append(poly([(lon, lat) for lat, lon in span], proj,
                            "rt-drive-line", 0.1, ' stroke-width="2.4"'))


def children_of(sheet) -> list[tuple[tuple, str]]:
    """The frames of later rungs that this sheet's ground contains.

    The overview boxes the two district sheets and the four town plans; the
    district sheets box the two plans cut out of them. Each sheet therefore
    says, on its own paper, where the next scale up is taken from.
    """
    w, s, e, n = sheet["frame"]
    out = []
    for other in P.SHEETS[P.SHEETS.index(sheet) + 1:]:
        for frame, title in [(other["frame"], other["short"])]:
            cw, cs, ce, cn = frame
            # Overlap, not containment: the Cascades sheet reaches further south
            # than this one can, and its box is worth drawing clipped rather than
            # not drawing it at all.
            mid_lat, mid_lon = (cs + cn) / 2, (cw + ce) / 2
            if s <= mid_lat <= n and w <= mid_lon <= e:
                out.append((frame, title))
    return out


def child_box(frame, proj: Proj, n: int, bounds=None) -> tuple[str, tuple]:
    """A later rung's ground, boxed and numbered.

    The number is the point. Spelling the sheet's name beside the box needs 120
    units of the busiest paper on the chart and lands on the Snoqualmie; an
    11-unit tag keyed to the apron list needs none of it, and it also makes the
    town-plan boxes findable, which at 8 units across they were not.
    """
    w, s, e, n_lat = frame
    x0, y0 = proj(w, n_lat)
    x1, y1 = proj(e, s)
    pad = 3.0
    bw, bh = max(x1 - x0, 4), max(y1 - y0, 4)
    rect = (x0 - pad, y0 - pad, bw + pad * 2, bh + pad * 2)
    tx, ty = rect[0] - 7.5, rect[1] - 7.5
    # A frame that starts at the sheet's own west edge puts its tag under the
    # apron, which is drawn last and paints over it: sheet 3 lost its number
    # that way. Keep the tag inside the map, flipping it in at the edges.
    if bounds:
        mx0, mx1 = bounds
        if tx - 6.5 < mx0 + 2:
            tx = rect[0] + 8.5
        if tx + 6.5 > mx1 - 2:
            tx = rect[0] + rect[2] - 8.5
        ty = max(ty, 9.0)
    return (f'<rect x="{rect[0]:.1f}" y="{rect[1]:.1f}" width="{rect[2]:.1f}" '
            f'height="{rect[3]:.1f}" fill="none" stroke="#7a4a2d" '
            f'stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>'
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="6.5" fill="#f7f1e0" '
            f'stroke="#7a4a2d" stroke-width="1"/>'
            f'<text x="{tx:.1f}" y="{ty + 3.2:.1f}" text-anchor="middle" '
            f'fill="#7a4a2d" style="font-size:9px; font-weight:600">{n}</text>',
            rect, (tx, ty))


def build_map_sheet(sheet, sizes: dict) -> str:
    """One rung of the ladder: a piece of ground at one honest scale."""
    frame = sheet["frame"]
    map_x, map_w, map_h = sheet_geometry(frame)
    proj = Proj(frame[0], frame[1], frame[2], frame[3], map_x, 0, map_w, map_h)
    print(f"  {sheet['key']}: {proj.px_per_km():.2f} units/km, map {map_x:.0f}"
          f"..{map_x + map_w:.0f}")

    out: list[str] = []
    # The index sheet is an index: its coast is read at 930 units for the whole
    # region, so 200 mm of shoreline detail is 40 KB nobody can see.
    draw_frame_content(proj, frame, out, sizes, sheet.get("eps", 0.7),
                       furniture=True)

    # The index sheet carries no drawings: at 3.5 units per km a doodle covers
    # 7 km of water, so every one of them belongs on a numbered sheet instead.
    # Canada keeps its geography and its names and gets no drawings at all.
    draws = sheet.get("doodles", True)
    usa_only = sheet.get("usa_only", True)
    only = sheet.get("only")

    def in_country(lat, lon):
        return in_country_of(lat, lon, usa_only)

    whale_notes = []
    for lat, lon in [d for d in P.WATER_DECO if on_frame(*d, frame, 0.03)]:
        x, y = proj(lon, lat)
        out.append(f'<path class="rt-water-deco" d="M {num(x)} {num(y)} '
                   f'q 6 -6 12 0 q 6 6 12 0"/>')
    places = [p for p in unique_places() if on_frame(*p["at"], frame)]
    anchors, displaced, dots, glyphs = fit_places(places, proj, sizes, sheet["key"],
                                                 sheet.get("doodles", True),
                                                 sheet.get("glyph_scale", 1.0))
    print(f"    places {len(places)}: doodle {len(anchors)}, nudged {len(displaced)}, "
          f"dot only {len(dots)}")
    # An index sheet names regions, waters and towns. It does not name the
    # bookshop: 117 printed names in a 930-unit map is what put Downriggers on
    # top of Rosario Strait. The rest keep their names on hover.
    towns_only = sheet.get("poi_names") == "towns"
    # Scenery is placed against the places, not before them: the placer already
    # holds every glyph box from fit_places.
    scenery = ([d for d in P.DOODLES + P.MARKS
                if on_frame(d[1], d[2], frame) and in_country(d[1], d[2])]
               if draws else [])
    doodles = []
    for ic, x, y, sc in fit_doodles(scenery, proj, sizes, glyphs):
        out.append(f'<use href="#sg-{ic}" transform="translate({x:.1f}, {y:.1f}) '
                   f'scale({sc})"/>')
        doodles.append((ic, x, y, sc))
    if draws:
        whales = [w for w in P.WHALES if on_frame(w[1], w[2], frame)
                  and in_country_of(w[1], w[2], usa_only)]
        for ic, wx, wy, sc in fit_doodles([(w[0], w[1], w[2], w[3]) for w in whales],
                                          proj, sizes, glyphs):
            out.append(f'<g transform="translate({wx:.1f}, {wy:.1f}) scale({sc})">'
                       f'<use href="#sg-{ic}"/></g>')
        for w in whales:
            if w[4]:
                x, y = proj(w[2], w[1])
                whale_notes.append((w[4], x, y))

    quiet = {p["key"] for p in places
             if is_quiet(p, sheet["key"])
             or (towns_only and p["key"] not in P.INDEX_NAMES)}
    # A place keeps its dot and its name everywhere; it only earns its drawing on
    # a sheet that draws, and only on the American side of the line.
    def plain(q):
        if only is not None and q["key"] not in only:
            return True          # a dot: this sheet is not about it
        return not draws or not in_country(*q["at"])

    # One placer for the whole sheet, built before anything is drawn, so the
    # hover labels compete for space with the printed names instead of ignoring
    # them.
    tags_pre = []
    for i2, (cf, _t) in enumerate(children_of(sheet), 1):
        _m, _r, tg = child_box(cf, proj, i2, (map_x, map_x + map_w))
        tags_pre.append(tg)
    placer = name_placer(proj, frame, glyphs, map_x, map_w, tags_pre)
    for ic, dx2, dy2, sc2 in [(d[0], d[1], d[2], d[3]) for d in doodles]:
        w2, h2 = sizes.get(ic, (24.0, 24.0))
        placer.blocks(dx2, dy2, max(w2 * abs(sc2), 10), max(h2 * abs(sc2), 10))
    hover_needed = [p for p in anchors + [d[0] for d in displaced]
                    if p["label"][0] == "hover" or p["key"] in quiet or plain(p)]
    hovers = place_hovers(hover_needed, proj, placer, sizes)
    gs = sheet.get("glyph_scale", 1.0)
    for a in anchors:
        out.append(poi_group(a, proj, scale=gs, quiet=a["key"] in quiet,
                             dot_only=plain(a),
                             named=draws and a["key"] not in quiet,
                             hover_at=hovers.get(a["key"])))
    for pl, dx, dy in displaced:
        x, y = poi_xy(pl, proj)
        out.append(f'<circle class="sg-dot" cx="{x:.1f}" cy="{y:.1f}" r="1.8"/>')
        out.append(f'<path class="rt-leader" d="M {num(x)} {num(y)} '
                   f'{num(x + dx)} {num(y + dy)}"/>')
        out.append(poi_group(pl, proj, at=(x + dx, y + dy), scale=gs,
                             quiet=pl["key"] in quiet, dot_only=plain(pl),
                             named=draws and pl["key"] not in quiet,
                             hover_at=hovers.get(pl["key"])))
    for pl in dots:
        out.append(poi_group(pl, proj, dot_only=True))

    children = children_of(sheet)
    tags = []
    for i, (cframe, title) in enumerate(children, 1):
        markup, rect, tag = child_box(cframe, proj, i, (map_x, map_x + map_w))
        out.append(markup)
        tags.append(tag)

    names(out, proj, frame, sizes, glyphs, anchors, displaced, doodles, whale_notes,
          map_x, map_w, tags, quiet, draws, placer, usa_only,
          lambda q: only is not None and q["key"] not in only)

    apron = map_apron(sheet, proj, map_x, map_w, dots, children)
    return wrap(sheet, proj, map_x, map_w, "".join(out), apron)


def name_placer(proj, frame, glyphs, map_x, map_w, tags=()):
    """The placer every name on a sheet shares: glyphs, tags, ticks, the apron."""
    placer = Placer()
    for box in glyphs.taken:
        placer.block(box)
    for tx, ty in tags:
        placer.blocks(tx, ty, 15, 15)
    for t, gx, gy, anchor in grid_ticks(proj, frame):
        placer.block(Placer.text_box(gx, gy, 0, 0, *_extent(t, "rt-flavor", 8.5),
                                     anchor, 0.0))
    far = 900
    placer.rect(-far, -far, map_x + 4, VB_H + far)
    placer.rect(map_x + map_w - 4, -far, VB_W + far, VB_H + far)
    placer.rect(-far, -far, VB_W + far, 6)
    placer.rect(-far, VB_H - 6, VB_W + far, VB_H + far)
    return placer


def place_hovers(places, proj, placer, sizes):
    """Where each hover label sits, chosen by the placer like any other name.

    On the index sheet these are the only names sixty dots have, and they were
    all pinned at a fixed offset: 43 of them landed on printed type.
    """
    out = {}
    for p in places:
        kind, dx, dy, anchor, cls, lines = p["label"]
        x, y = poi_xy(p, proj)
        ndx, ndy, na = placer.place(list(lines), x, y, "rt-sub", anchor or "start",
                                    dx or 11, dy or 4)
        out[p["key"]] = (ndx, ndy, na)
    return out


def names(out, proj, frame, sizes, glyphs, anchors, displaced, doodles,
          whale_notes, map_x, map_w, tags=(), quiet=frozenset(), draws=True,
          placer=None, usa_only=True, off_topic=lambda q: False):
    """Every name on the sheet, placed so it lands on nothing already there."""
    if placer is None:
        placer = name_placer(proj, frame, glyphs, map_x, map_w, tags)
    for ic, x, y, sc in doodles:
        w, h = sizes.get(ic, (24.0, 24.0))
        placer.blocks(x, y, max(w * abs(sc), 10), max(h * abs(sc), 10))


    summits = [s for s in P.SUMMITS if on_frame(*s["at"], frame)]
    for s in summits:
        if not (draws and in_country_of(*s["at"], usa_only)):
            continue
        x, y = proj(s["at"][1], s["at"][0])
        w, h = sizes.get(s["glyph"], (60.0, 44.0))
        sc = s.get("scale", 1.0)
        placer.blocks(x, y - h * sc / 4, w * sc, h * sc)

    labels = [l for l in P.LABELS if on_frame(l[1], l[2], frame)
              and (draws or l[0] not in P.INDEX_OMIT_LABELS)]
    for t, (lat, lon), dx, dy, anchor in [p for p in P.PASSES
                                          if on_frame(*p[1], frame)]:
        x, y = proj(lon, lat)
        if draws:
            out.append(f'<use href="#sg-saddle" '
                       f'transform="translate({x:.1f}, {y:.1f})"/>')
        placer.blocks(x, y, 26, 20)
        dx, dy, anchor = placer.place([t], x, y, "rt-sub", anchor, dx, dy)
        out.append(text(t, x + dx, y + dy, "rt-sub", anchor))
    for s in summits:
        x, y = proj(s["at"][1], s["at"][0])
        sc = s.get("scale")
        tr = f' scale({sc})' if sc else ""
        out.append("<g>" if s.get("visited") else '<g class="rt-unvisited">')
        if draws and in_country_of(*s["at"], usa_only):
            out.append(f'<use href="#sg-{s["glyph"]}" '
                       f'transform="translate({x:.1f}, {y:.1f}){tr}"/>')
        t, dx, dy, anchor = s["label"]
        if t:
            dx, dy, anchor = placer.place([t], x, y, "rt-sub", anchor, dx, dy)
            out.append(text(t, x + dx, y + dy, "rt-sub", anchor))
        out.append("</g>")

    # A drawing sheet has room to say what it is drawing. Deception Pass and
    # Gas Works Park are hover-only on the hand-drawn chart because it has 56
    # places in one frame; here they get their name printed.
    for a in anchors:
        out.append(poi_label(a, proj, placer, quiet=a["key"] in quiet,
                             subs=draws, loud=draws and not off_topic(a)))
    for p, dx, dy in displaced:
        out.append(poi_label(p, proj, placer, off=(dx, dy),
                             quiet=p["key"] in quiet, subs=draws, loud=draws))
    for note, x, y in whale_notes:
        dx, dy, anchor = placer.place([note], x, y, "rt-flavor", "middle", 0, 22)
        out.append(text(note, x + dx, y + dy, "rt-flavor", anchor))

    def wrap_seen(t, lat, lon, body):
        if t in P.UNVISITED_LABELS or P.in_unvisited_region(lat, lon):
            return f'<g class="rt-unvisited">{body}</g>'
        return body

    for t, lat, lon, cls, anchor, rot in labels:
        if not rot:
            x, y = proj(lon, lat)
            dx, dy, anchor = placer.place([t], x, y, cls, anchor, 0, -12)
            piece = ""
            if math.hypot(dx, dy) > 26:
                piece += leader(x, y, x + dx, y + dy, anchor)
            piece += text(t, x + dx, y + dy, cls, anchor)
            out.append(wrap_seen(t, lat, lon, piece))
    for t, lat, lon, cls, anchor, rot in labels:
        if rot:
            x, y = proj(lon, lat)
            dx, dy, anchor = placer.place([t], x, y, cls, anchor, 0, 0, rot)
            out.append(wrap_seen(t, lat, lon,
                                 text(t, x + dx, y + dy, cls, anchor, rot)))
    for t, (lat, lon), rot in (("CANADA", (48.7600, -123.3000), -40),
                               ("U.S.A.", (48.4600, -123.1000), -76)):
        if not on_frame(lat, lon, frame):
            continue
        x, y = proj(lon, lat)
        dx, dy, anchor = placer.place([t], x, y, "rt-flavor", "middle", 0, 0, rot)
        out.append(text(t, x + dx, y + dy, "rt-flavor", anchor, rot))
    for leg in (P.DRIVE_LEGS if draws else []):
        for key in ("label", "label2"):
            if not leg.get(key):
                continue
            t, lat, lon, rot = leg[key]
            if not on_frame(lat, lon, frame):
                continue
            x, y = proj(lon, lat)
            dx, dy, anchor = placer.place([t], x, y, "rt-sub", "middle", 0, 0, rot)
            out.append(text(t, x + dx, y + dy, "rt-sub", anchor, rot))
    for t, lat, lon, rot in ([r for r in P.RIVER_LABELS
                              if on_frame(r[1], r[2], frame)] if draws else []):
        x, y = proj(lon, lat)
        dx, dy, anchor = placer.place([t], x, y, "rt-flavor", "middle", 0, 0, rot, 8.5)
        out.append(text(t, x + dx, y + dy, "rt-flavor", anchor, rot, size=8.5))


def locator_inset(sheet, x, y, width) -> str:
    """This sheet's ground, boxed inside the whole Salish Sea.

    Without it a reader who lands on sheet 2 has a coastline and no idea which
    coastline. It is the same projection, three coarse strokes, and a box.
    """
    whole = overview_frame()
    if sheet["frame"] == whole or sheet.get("no_locator"):
        return ""
    proj = Proj.fit_width(whole[0], whole[1], whole[2], whole[3], x, y, width)
    bx, by, bw, bh = proj.box
    land, _ = land_rings(whole)
    out = [f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
           f'fill="#e7ece2" stroke="#c9d2be" stroke-width="1"/>',
           f'<path d="{path_d(land, proj, 2.2)}" fill="#d7dfcd" stroke="#b3bfa3" '
           f'stroke-width="0.6"/>']
    w, s, e, n = sheet["frame"]
    x0, y0 = proj(w, n)
    x1, y1 = proj(e, s)
    # Clamped to the locator's own box: the Vancouver sheet sits mostly north of
    # the index frame, and an unclamped rectangle ran up through the legend.
    cx0, cy0 = max(x0, bx), max(y0, by)
    cx1, cy1 = min(x1, bx + bw), min(y1, by + bh)
    if cx1 - cx0 > 2 and cy1 - cy0 > 2:
        out.append(f'<rect x="{cx0:.1f}" y="{cy0:.1f}" width="{cx1 - cx0:.1f}" '
                   f'height="{cy1 - cy0:.1f}" fill="#7a4a2d" fill-opacity="0.18" '
                   f'stroke="#7a4a2d" stroke-width="1.2"/>')
    out.append(text("this sheet, in the whole water", bx, by + bh + 12,
                    "rt-sub", "start", size=9))
    return "".join(out)


# ----------------------------------------------------------------- the aprons

def legend_rows(x, y0, keys=None):
    """The legend, flowed rather than fixed.

    Each row draws itself at whatever y it lands on, so a sheet that has no
    trail and no international boundary loses those two rows instead of
    printing them over empty paper.
    """
    rows = [
        ("ferry", lambda y: f'<path class="rt-ferry-line" '
                            f'marker-end="url(#sg-track-arrow)" d="M {x} {y} h 30"/>',
         ["Washington State Ferries"]),
        ("drive", lambda y: f'<path class="rt-drive-line" d="M {x} {y} h 34"/>',
         ["Drive"]),
        ("trail", lambda y: f'<path class="rt-trail-line" d="M {x} {y} h 34"/>',
         ["Trail"]),
        ("terminal", lambda y: f'<use href="#sg-anchor" '
                               f'transform="translate({x + 17}, {y}) scale(0.85)"/>',
         ["Ferry terminal"]),
        ("border", lambda y: f'<path class="rt-border" d="M {x} {y} h 34"/>',
         ["International boundary"]),
        ("crest", lambda y:
            f'<path fill="none" stroke="#5d6b3f" stroke-width="2" '
            f'stroke-linecap="round" d="M {x} {y + 1} C {x + 8} {y - 1}, '
            f'{x + 18} {y + 3}, {x + 34} {y}"/>'
            f'<path fill="none" stroke="#6f7e4a" stroke-width="1.1" '
            f'stroke-linecap="round" opacity="0.75" d="M {x + 3} {y - 2} l 2 -6 '
            f'M {x + 10} {y} l 1 -6 M {x + 17} {y + 1} l 2 -6 '
            f'M {x + 24} {y + 2} l 1 -6 M {x + 31} {y} l 2 -6"/>',
         ["Cascade crest, the divide"]),
        ("river", lambda y: f'<path d="M {x} {y} C {x + 10} {y - 6}, '
                            f'{x + 24} {y + 6}, {x + 34} {y}" fill="none" '
                            f'stroke="#aac4d1" stroke-width="2.6" opacity="0.8" '
                            f'stroke-linecap="round"/>',
         ["River"]),
        ("box", lambda y: f'<rect x="{x}" y="{y - 6}" width="34" height="12" '
                          f'fill="none" stroke="#7a4a2d" stroke-width="1" '
                          f'stroke-dasharray="3 3" opacity="0.8"/>',
         ["Drawn again, larger, on", "a later sheet"]),
        ("dot", lambda y: f'<circle class="sg-dot" cx="{x + 17}" cy="{y}" r="2.2"/>',
         ["A place whose doodle is", "on a later sheet"]),
    ]
    out, y = [], y0
    for key, draw, lines in rows:
        if keys is not None and key not in keys:
            continue
        out.append(draw(y))
        for i, line in enumerate(lines):
            out.append(f'<text class="rt-quest-item" x="{x + 44}" '
                       f'y="{y + 4 + i * 12}">{line}</text>')
        y += 20 + (len(lines) - 1) * 12
    return "".join(out), y


LEGEND_ALL = ("ferry", "drive", "trail", "terminal", "border", "crest", "river",
              "box", "dot")


def legend_keys(sheet, frame, children, dots) -> tuple:
    """Only the legend rows this sheet's ground actually shows."""
    box = grow(frame)
    keys = []
    if any(on_frame(lat, lon, frame, -0.02) for leg in P.FERRY_LEGS
           for lat, lon in leg):
        keys.append("ferry")
    keys.append("drive")
    if any(on_frame(lat, lon, box) for t in P.TRAILS for lat, lon in t):
        keys.append("trail")
    if any(on_frame(*p["at"], frame) for p in P.POIS if p.get("ic") == "anchor"):
        keys.append("terminal")
    if any(on_frame(lat, lon, box) for b in (P.BORDER, P.BORDER_49)
           for lat, lon in b):
        keys.append("border")
    if any(on_frame(lat, lon, box) for lat, lon in P.CREST):
        keys.append("crest")
    if rivers(frame):
        keys.append("river")
    if children:
        keys.append("box")
    if dots:
        keys.append("dot")
    return tuple(keys)


def map_apron(sheet, proj: Proj, map_x, map_w, dots, children) -> str:
    """The paper either side of the map: title, note, bar, legend, locator.

    One function for every rung. The overview had its own, with its own copy and
    its own fixed y for each block, which is why adding a sheet meant either
    forking it or writing the Seattle sheet's apron by hand.
    """
    x = 30
    frame = sheet["frame"]
    out = [f'<rect x="0" y="0" width="{map_x}" height="{VB_H}" class="sg-apron"/>',
           f'<rect x="{map_x + map_w}" y="0" width="{VB_W - map_x - map_w}" '
           f'height="{VB_H}" class="sg-apron"/>',
           f'<path class="sg-apron-rule" d="M {map_x} 0 V {VB_H} '
           f'M {map_x + map_w} 0 V {VB_H}"/>',
           f'<text class="rt-label big" x="{x}" y="52" text-anchor="start" '
           f'style="font-size:19px; letter-spacing:0.8px;">{sheet["title"]}</text>',
           text(sheet["sub"], x, 74, "rt-flavor", "start")]
    for i, line in enumerate(sheet["blurb"]):
        out.append(text(line, x, 100 + i * 13, "rt-sub", "start"))
    y = 100 + len(sheet["blurb"]) * 13 + 14

    bar, bar_w = scale_bar(x, y + 14, proj)
    out.append(bar)
    base = next(s2 for s2 in P.SHEETS if s2["key"] == "overview")
    base_upk = sheet_geometry(base["frame"])[0] and 900.0 / (
        (base["frame"][3] - base["frame"][1]) * 110.9)
    k = proj.px_per_km()
    note = f"{k:.1f} units per km" if k < 10 else f"{k:.0f} units per km"
    if sheet["key"] != "overview":
        note += f" · {k / base_upk:.0f}× the index sheet"
    out.append(text(note, x, y + 34, "rt-sub", "start", size=9))
    # The compass goes after the bar's actual end, not at a fixed offset.
    out.append(compass(x + bar_w + 30, y + 4))
    y += 62

    out.append(text("Legend", x, y, "rt-quest-title", "start"))
    body, y = legend_rows(x, y + 18, legend_keys(sheet, frame, children, dots))
    out.append(body)

    if children:
        y += 10
        out.append(text("Drawn larger further along", x, y, "rt-quest-title", "start"))
        out.append(text("places", x + 250, y, "rt-sub", "end", size=8.5))
        y += 20
        for i, (cframe, title) in enumerate(children, 1):
            n = len([p for p in unique_places() if on_frame(*p["at"], cframe)])
            out.append(f'<circle cx="{x + 6.5}" cy="{y - 3.5}" r="6.5" '
                       f'fill="#f7f1e0" stroke="#7a4a2d" stroke-width="1"/>'
                       f'<text x="{x + 6.5}" y="{y - 0.3}" text-anchor="middle" '
                       f'fill="#7a4a2d" style="font-size:9px; font-weight:600">'
                       f'{i}</text>')
            out.append(text(title, x + 19, y, "rt-sub", "start", size=9))
            out.append(text(str(n), x + 250, y, "rt-sub", "end", size=9))
            y += 17

    loc = locator_inset(sheet, x, min(y + 18, VB_H - 150), 190)
    out.append(loc)

    rx = map_x + map_w + 16
    out.append(text("Coastlines, lakes,", rx, 828, "rt-sub", "start", size=9))
    out.append(text("rivers and highways:", rx, 841, "rt-sub", "start", size=9))
    out.append(text("OpenStreetMap. Drives", rx, 854, "rt-sub", "start", size=9))
    out.append(text("routed on the real", rx, 867, "rt-sub", "start", size=9))
    out.append(text("highway network.", rx, 880, "rt-sub", "start", size=9))
    return "".join(out)


# ------------------------------------------------------------------- assembly

def wrap(sheet, proj, map_x, map_w, body: str, apron: str, narrow_vb=None) -> str:
    """One sheet as an svg: the map clipped, the apron over it."""
    if proj is not None:
        clip = (f'<clipPath id="sg-clip-{sheet["key"]}"><rect x="{map_x}" y="0" '
                f'width="{map_w}" height="{VB_H}"/></clipPath>')
        inner = f'<g clip-path="url(#sg-clip-{sheet["key"]})">{body}</g>'
        narrow = f' data-map-only="{map_x:.0f} 0 {map_w:.0f} {VB_H:.0f}"'
    else:
        clip, inner = "", body
        narrow = f' data-map-only="{narrow_vb}"' if narrow_vb else ""
    return (f'<svg class="sg-sheet" id="sg-sheet-{sheet["key"]}" '
            f'viewBox="0 0 {VB_W:.0f} {VB_H:.0f}"{narrow} '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{sheet["title"]}: {sheet["sub"]}">'
            f'<defs>{{DEFS}}{clip}</defs>{inner}'
            f'<g class="sg-apron-layer">{apron}</g></svg>')


def subset_defs(defs: str, markup: str) -> str:
    """Only the glyphs this sheet actually uses.

    Four sheets carrying four copies of a 56 KB glyph library is 200 KB of the
    same drawing; a sheet typically uses a third of it.
    """
    blocks = dict(re.findall(r'(<g id="sg-([a-z_-]+)")', defs))
    used = set(re.findall(r'href="#sg-([a-z_-]+)"', markup))
    out = []
    for m in re.finditer(r'<g id="sg-([a-z_-]+)".*?(?=<g id="sg-|<marker |$)', defs, re.S):
        if m.group(1) in used:
            out.append(m.group(0))
    marker = re.search(r'<marker id="sg-track-arrow".*?</marker>', defs, re.S)
    if marker and "sg-track-arrow" in markup:
        out.append(marker.group(0))
    return "".join(out)


def section_html(sheets: list[str]) -> str:
    slides = "".join(f'<div class="sg-slide">{s}</div>' for s in sheets)
    return f'''{BEGIN}
    <!-- The same Salish Sea chart, to scale, on its own screen: a ladder of
         sheets, each at one honest scale. Generated: edit
         scripts/salish_places.py and rebuild, never this markup. -->
    <section id="salish-to-scale" aria-hidden="true"
             aria-label="Salish Sea routes, drawn to scale">
        <button class="back-to-globe sg-up" type="button" data-target="pnw-section">
            <span aria-hidden="true">↑</span> Charts
        </button>
        <button class="sg-nav prev" type="button" aria-label="Previous sheet" disabled>
            <span aria-hidden="true">‹</span>
        </button>
        <button class="sg-nav next" type="button" aria-label="Next sheet">
            <span aria-hidden="true">›</span>
        </button>
        <div class="sg-pager" id="sgPager">{slides}</div>
        <div class="sg-dots" id="sgDots" role="tablist" aria-label="Chart sheets"></div>
    </section>
    {END}'''


def main() -> int:
    html = MAPS.read_text()
    defs_all = panel2_defs(html)
    sizes = glyph_extents(defs_all)
    print(f"glyphs measured: {len(sizes)}")

    built = []
    for sheet in P.SHEETS:
        print(f"sheet {sheet['key']} ({sheet['kind']})")
        svg = build_map_sheet(sheet, sizes)
        svg = svg.replace("{DEFS}", subset_defs(defs_all, svg))
        print(f"    {len(svg) // 1024} KB")
        built.append(svg)

    coverage(sizes)

    style = re.search(r"<style>(.*?)</style>", html, re.S)
    Path("/tmp/salish_preview.html").write_text(
        "<!doctype html><meta charset=utf-8><style>"
        + (style.group(1) if style else "")
        + "html,body{margin:0;height:100%;background:#f4f6f1}"
        + "#salish-to-scale{opacity:1;transform:none}"
        + ".sg-pager{scroll-snap-type:none}</style>"
        + '<section id="salish-to-scale">'
        + '<div class="sg-pager">'
        + "".join(f'<div class="sg-slide">{s}</div>' for s in built)
        + "</div></section>")
    for i, svg in enumerate(built):
        Path(f"/tmp/salish_sheet{i + 1}.html").write_text(
            "<!doctype html><meta charset=utf-8><style>"
            + (style.group(1) if style else "")
            + "html,body{margin:0;height:100%;background:#f4f6f1}"
            + "svg{display:block;width:100vw;height:100vh}</style>" + svg)
    print("preview /tmp/salish_preview.html  and /tmp/salish_sheet1.html ...")

    if "--preview" in sys.argv:
        return 0
    if BEGIN not in html:
        raise SystemExit("markers not found in maps.html")
    html = re.sub(re.escape(BEGIN) + ".*?" + re.escape(END), section_html(built),
                  html, flags=re.S)
    MAPS.write_text(html)
    print(f"wrote   {MAPS}")
    return 0


def coverage(sizes: dict) -> None:
    """Does every place get a doodle on at least one sheet?

    Only places panel 2 draws a glyph for can answer yes. The handful it marks
    with a bare chart stop are counted separately: their whole appearance is the
    dot, and the overview carries it.
    """
    homes: dict[str, list[str]] = {}
    for sheet in P.SHEETS:
        for frame in sheet_frames(sheet):
            map_x, map_w, map_h = sheet_geometry(frame)
            proj = Proj(frame[0], frame[1], frame[2], frame[3],
                        map_x, 0, map_w, map_h)
            inside = [p for p in unique_places() if on_frame(*p["at"], frame)]
            anchors, displaced, dots, _ = fit_places(inside, proj, sizes,
                                                     sheet["key"])
            for p in anchors + [d[0] for d in displaced]:
                homes.setdefault(p["key"], []).append(sheet["key"])
    places = unique_places()
    drawn = [p for p in places if p.get("ic")]
    stops = [p for p in places if not p.get("ic")]
    missing = [p for p in drawn if p["key"] not in homes]
    print(f"coverage: {len(drawn) - len(missing)} of {len(drawn)} places with a "
          f"glyph have their doodle on some sheet")
    lost = [p for p in stops if p["key"] not in homes]
    print(f"          {len(stops) - len(lost)} of {len(stops)} glyph-less chart "
          f"stops are drawn as a dot at their true position")
    for label, group in (("no doodle anywhere", missing), ("stop not drawn", lost)):
        if group:
            print(f"  {label}:")
            for m in sorted(p["name"] for p in group):
                print(f"    {m}")


if __name__ == "__main__":
    raise SystemExit(main())
