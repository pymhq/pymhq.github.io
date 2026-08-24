"""Draw one panel per start line, on the real ground, and write them into maps.html.

What this replaces
------------------
The race chart used to be a single hand-drawn sheet of Puget Sound with ten
short squiggles on it, each at an invented position, each the same shape. You
could not tell the Lake Union loop from the Waterfront out-and-back, because
neither was actually drawn. Ten events sharing one sheet is a list, not a map.

What this is
------------
One panel per event, in the language a workout summary uses: the course big, on
the real street network it is run on, with the numbers beside it. Every course
is the organiser's own published line - see scripts/race_courses.py for where
each one comes from - and every street, park and shoreline under it is
OpenStreetMap. Nothing here is drawn by hand and nothing is moved.

The frame of each panel is set by its own course, so the Pumpkin Dash mile and
the Boston 10K are each drawn as large as their own paper allows: the scale bar
on each panel says what that came to. That is the opposite convention from the
Salish sheets, which hold one scale across a ladder of frames, and it is right
here for the same reason it is wrong there. These are nine separate mornings in
four cities, not one body of water.

    python3 scripts/build_race_panels.py            # write into maps.html
    python3 scripts/build_race_panels.py --preview  # /tmp only, don't touch the page
    python3 scripts/build_race_panels.py --only boston_10k
"""

from __future__ import annotations

import heapq
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_courses as R                                    # noqa: E402
import salish_geo as SG                                     # noqa: E402
from fetch_race_geo import CACHE, COURSES, frame_of         # noqa: E402
from salish_geo import (                                    # noqa: E402
    Proj, clip_chain, merc_x, merc_y, num, path_d, points_d, rdp,
    stitch, way_coords,
)

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps.html"

BEGIN = "<!-- BEGIN generated: race panels (scripts/build_race_panels.py) -->"
END = "<!-- END generated: race panels -->"

# One panel is 900 units tall and as wide as its own course needs, up to 16:9.
#
# There used to be a 470-unit rail down the left side carrying the title, one
# date and the venue. Three short blocks in a 470x900 column is a column of
# empty paint, and the map paid for it twice: it lost a third of its width, and
# what was left was the wrong shape for a course, so a north-south course like
# the Waterfront 5K sat hard against one edge with a screen of bay beside it.
# The title is now set on the map itself, in whichever top corner the course is
# furthest from.
#
# The width is the other half of the same problem. Only the Boston course is
# 16:9; the rest are portrait, and the streets are only fetched for the course's
# own box, so a panel wider than that box is not map, it is unpainted paper with
# the streets stopping dead in the middle of it. So each panel is cut to the
# shape of its own ground - between 620 units and the full 1600 - and the pager
# centres it on the screen. Nothing is lost: what filled that width before was
# blank.
VB_H = 900.0
VB_W = 1600.0             # the widest a panel gets, and the shape of the screen
PANEL_MIN_W = 620.0       # enough paper for the title block
MAP_X = 0.0

# The type block: the corner is chosen per panel, the size follows the panel.
PAD = 44.0
BLOCK_H = 180.0
# The page's nav is sticky, so it sits over the top of a full-height panel: about
# 80 of the 860 css pixels a 900-unit panel is scaled into. The top block starts
# below that, which is also why the bottom of the panel is not treated the same
# way - nothing overlays it but the pager's own dots, and those are centred.
HEADER_CLEAR = 96.0

# The dark set. A race panel is not a chart: it is a screen you look at once,
# after, to see what you did. So it reads like an instrument and not like paper,
# and the parchment palette of every other panel on this page is deliberately
# not used here.
INK = "#e9eef4"          # primary type
DIM = "#8d99a6"          # labels, secondary type
FAINT = "#5b6672"        # provenance
BG = "#0e1216"           # the map's paper
WATER = "#16324a"
WATER_EDGE = "#23536f"
GREEN = "#152318"
ROAD_MAJOR = "#39424d"
ROAD_MINOR = "#242c34"
PATH = "#2c3540"
RAIL_LINE = "#2a2f38"


# ------------------------------------------------------------------ osm layers

def load(key: str, layer: str) -> list:
    f = CACHE / f"{key}-{layer}.json"
    if not f.exists():
        return []
    return json.loads(f.read_text()).get("elements", [])


def rings_of(el: dict) -> tuple[list, list]:
    """Outer and inner rings of a way or multipolygon relation."""
    if el["type"] == "way":
        c = way_coords(el)
        return ([c] if len(c) > 3 else []), []
    outer = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
             for m in el.get("members", []) if m.get("role") in ("outer", "")]
    inner = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
             for m in el.get("members", []) if m.get("role") == "inner"]
    keep = lambda rs: [r for r in stitch([x for x in rs if len(x) > 1]) if len(r) > 3]
    return keep(outer), keep(inner)


# Sidewalks and crossings are 80% of the footway layer and none of the
# information: on the Lake Union panel they drew a grey fur along every street
# that already had a line. Named paths, trails and cycleways stay, because the
# Burke-Gilman and the Sammamish River Trail are what three of these races are.
SIDEWALK = {"sidewalk", "crossing", "traffic_island", "access"}


def path_chains(key: str) -> list:
    out = []
    for el in load(key, "paths"):
        t = el.get("tags", {})
        if t.get("footway") in SIDEWALK or t.get("cycleway") == "crossing":
            continue
        if t.get("highway") == "footway" and not t.get("name"):
            continue
        c = way_coords(el)
        if len(c) > 1:
            out.append(c)
    return out


ROAD_WEIGHT = {
    "motorway": 3.4, "motorway_link": 2.0, "trunk": 3.0, "trunk_link": 1.8,
    "primary": 2.6, "primary_link": 1.6, "secondary": 2.1, "secondary_link": 1.4,
    "tertiary": 1.7, "tertiary_link": 1.2, "residential": 1.1,
    "unclassified": 1.1, "living_street": 1.0, "pedestrian": 1.2,
}


def road_chains(key: str) -> dict[float, list]:
    out: dict[float, list] = defaultdict(list)
    for el in load(key, "roads"):
        cls = el.get("tags", {}).get("highway", "")
        w = ROAD_WEIGHT.get(cls)
        c = way_coords(el)
        if w and len(c) > 1:
            out[w].append(c)
    return out


# ------------------------------------------------------------------- the course

def course_of(race: dict) -> list:
    """The measured line, or the one routed through the printed turns."""
    if race.get("course"):
        pts = json.loads((COURSES / f"{race['course']}.json").read_text())
        return [(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in pts]
    if race.get("route"):
        r = race["route"]
        return Streets(race["key"], r.get("classes")).route(r["waypoints"])
    return []


class Streets:
    """The street and track network as a graph, so a course can be routed on it.

    Two courses need this. Boston, because the B.A.A. publishes a picture rather
    than a track: drawing that by hand would put the turns wherever the hand went,
    so the turns its own map names are given as waypoints and the line between
    them is the real street. And Tough Mudder Seattle, because the course was
    never a street at all - it was two laps of the forest roads and pit tracks of
    a working coal property - so the graph is restricted to tracks and paths and
    the circuit is routed on those.

    The graph is undirected: a road race closes the street, so one-way is not a
    constraint on the runner. Ways that stop a few metres short of each other are
    sewn, because a track network mapped way by way is full of such gaps and
    without sewing the venue's own network arrives in 200 pieces.
    """

    def __init__(self, key: str, classes=None) -> None:
        self.pos: dict[int, tuple[float, float]] = {}
        self.adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
        for el in load(key, "roads") + load(key, "paths"):
            if classes and el.get("tags", {}).get("highway") not in classes:
                continue
            nodes, geom = el.get("nodes", []), el.get("geometry", [])
            if len(nodes) != len(geom) or len(nodes) < 2:
                continue
            for nid, p in zip(nodes, geom):
                if p:
                    self.pos[nid] = (p["lon"], p["lat"])
            for a, b in zip(nodes, nodes[1:]):
                if a in self.pos and b in self.pos:
                    d = _d(self.pos[a], self.pos[b])
                    self.adj[a].append((b, d))
                    self.adj[b].append((a, d))
        self.main = self._sew()
        print(f"    graph: {len(self.pos)} nodes, largest piece {len(self.main)}")

    def _sew(self) -> set:
        """Join ways whose ends nearly touch, and report the largest piece.

        Thirty metres, at three times the cost so the router only ever uses a
        seam to cross one. Then the biggest connected piece is the network the
        course is on: snapping a waypoint to the globally nearest node put the
        Tough Mudder start on the property's entrance stub, which is ten nodes
        long and goes nowhere.
        """
        par = {n: n for n in self.pos}

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        for u, es in self.adj.items():
            for v, _w in es:
                a, b = find(u), find(v)
                if a != b:
                    par[a] = b
        span = 0.0004
        buck: dict[tuple[int, int], list[int]] = defaultdict(list)
        for n, (lo, la) in self.pos.items():
            buck[(int(la / span), int(lo / span))].append(n)
        cand = []
        for n, (lo, la) in self.pos.items():
            bx, by = int(la / span), int(lo / span)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for o in buck.get((bx + dx, by + dy), ()):
                        if o <= n or find(o) == find(n):
                            continue
                        d = _d(self.pos[n], self.pos[o])
                        if d < 0.00040:
                            cand.append((d, n, o))
        cand.sort()
        for d, a, b in cand:
            if find(a) == find(b):
                continue
            par[find(a)] = find(b)
            self.adj[a].append((b, d * 3))
            self.adj[b].append((a, d * 3))
        groups: dict[int, set] = defaultdict(set)
        for n in self.pos:
            groups[find(n)].add(n)
        return max(groups.values(), key=len) if groups else set()

    def nearest(self, lat: float, lon: float) -> int:
        pool = self.main or self.pos
        return min(pool, key=lambda n: _d(self.pos[n], (lon, lat)))

    def route(self, waypoints) -> list:
        nodes = [self.nearest(lat, lon) for lat, lon in waypoints]
        path: list[tuple[float, float]] = []
        for a, b in zip(nodes, nodes[1:]):
            leg = self._dijkstra(a, b)
            if not leg:
                print(f"    ! no street path {self.pos[a]} -> {self.pos[b]}")
                leg = [self.pos[a], self.pos[b]]
            path += leg if not path else leg[1:]
        return [(lat, lon, 0.0) for lon, lat in path]

    def _dijkstra(self, a: int, b: int):
        dist = {a: 0.0}
        prev: dict[int, int] = {}
        q = [(0.0, a)]
        while q:
            d, u = heapq.heappop(q)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in self.adj[u]:
                nd = d + w
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


def _d(p, q) -> float:
    return math.hypot((p[0] - q[0]) * 0.67, p[1] - q[1])


def km(a, b) -> float:
    return math.hypot((b[0] - a[0]) * 110.9,
                      (b[1] - a[1]) * 111.32 * math.cos(math.radians((a[0] + b[0]) / 2)))


def cumulative(pts) -> list[float]:
    out = [0.0]
    for i in range(len(pts) - 1):
        out.append(out[-1] + km(pts[i][:2], pts[i + 1][:2]))
    return out


# ---------------------------------------------------------------------- drawing

def panel_width(race: dict) -> float:
    """How wide this panel's paper is: the shape of the ground it has.

    The fetched box is the course plus a fifth of its span, and that is exactly
    the ground there are streets for, so the panel is that box's own aspect. Wider
    than 16:9 is more than a screen holds, and narrower than PANEL_MIN_W has no
    room for the title, so it is clamped at both ends: the three narrowest courses
    still carry a band of paper the streets do not reach, and on all three that
    band is Elliott Bay or Lake Washington, which the coastline cache does paint.
    """
    w, s, e, n = frame_of(race)
    dx = merc_x(e) - merc_x(w)
    dy = merc_y(n) - merc_y(s)
    return min(VB_W, max(PANEL_MIN_W, round(VB_H * dx / dy)))


def frame_for_panel(race: dict, pw: float) -> tuple:
    """The fetched frame, squared up to the panel so nothing is stretched.

    The projection keeps one scale on both axes and centres the slack, so a tall
    course in a wide box is correct but small and off to one side. Growing the
    short axis of the frame instead fills the box, at the same scale, with real
    ground rather than with padding. With the panel cut to the course's own shape
    this is now a small correction on most panels instead of a third of the width.
    """
    w, s, e, n = frame_of(race)
    want = pw / VB_H
    dx = merc_x(e) - merc_x(w)
    dy = merc_y(n) - merc_y(s)
    if dx / dy < want:
        grow = (want * dy - dx) / 2
        w = math.degrees(merc_x(w) - grow)
        e = math.degrees(merc_x(e) + grow)
    else:
        grow = (dx / want - dy) / 2
        s = math.degrees(2 * math.atan(math.exp(merc_y(s) - grow)) - math.pi / 2)
        n = math.degrees(2 * math.atan(math.exp(merc_y(n) + grow)) - math.pi / 2)
    return (w, s, e, n)


def lines_on(chains, proj, rect, cls_attr: str, eps: float = 0.9) -> list[str]:
    """Every chain of one class as a single path element.

    One <path> per street is 70 bytes of repeated attributes per street, and the
    Lake Union panel has 2,369 streets and 14,000 paths in frame: that alone was
    460 KB of the same six attributes. SVG lets one path carry any number of
    subpaths, so a class of street is one element and the weight is only the
    coordinates.
    """
    ds = []
    for ch in chains:
        for piece in clip_chain(ch, rect):
            if len(piece) < 2:
                continue
            pts = rdp([proj(lo, la) for lo, la in piece], eps)
            if len(pts) > 1:
                ds.append(points_d(pts, False))
    return [f'<path {cls_attr} d="{" ".join(ds)}"/>'] if ds else []


def bbox_of(el: dict) -> tuple | None:
    b = el.get("bounds")
    if b:
        return (b["minlon"], b["minlat"], b["maxlon"], b["maxlat"])
    geom = el.get("geometry") or []
    if not geom:
        return None
    lons = [p["lon"] for p in geom if p]
    lats = [p["lat"] for p in geom if p]
    return (min(lons), min(lats), max(lons), max(lats)) if lons else None


def touches(el: dict, rect) -> bool:
    b = bbox_of(el)
    if not b:
        return True
    w, s, e, n = rect
    return not (b[2] < w or b[0] > e or b[3] < s or b[1] > n)


def areas_on(elements, proj, rect, fill: str, stroke: str = "none",
             eps: float = 0.6, opacity: float = 1.0) -> list[str]:
    """Filled polygons, projected whole and left to the panel's own clip.

    Clipping a water polygon to the frame geometrically is where this first went
    wrong: Lake Washington's outer ring enters and leaves the Seward Park frame,
    and joining the pieces along the frame edge closed the polygon round the land
    instead of round the lake, so the whole panel came out as water. The panel
    already has an SVG clip on its map group, and an SVG clip cannot get the
    inside and the outside the wrong way round. So the ring is projected in full
    and simplified in panel units, which folds the part outside the frame down to
    a handful of points and costs almost nothing.
    """
    ds = []
    for el in elements:
        if not touches(el, rect):
            continue
        outer, inner = rings_of(el)
        rings = []
        for ring in outer + inner:
            pts = rdp([proj(lo, la) for lo, la in ring], eps)
            # A 6-unit lawn is not information at 1:12,000; it is three hundred
            # of them turning the parks layer into noise and 80 KB of file.
            if len(pts) > 2 and _span(pts) > 9.0:
                rings.append(points_d(pts, True))
        if rings:
            ds.append(" ".join(rings))
    if not ds:
        return []
    extra = f' stroke="{stroke}" stroke-width="1"' if stroke != "none" else ""
    return [f'<path d="{" ".join(ds)}" fill="{fill}" fill-opacity="{opacity}"'
            f' fill-rule="evenodd"{extra}/>']


def _span(pts) -> float:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def scale_bar(x: float, y: float, proj: Proj, want: float = 190.0) -> str:
    upk = proj.px_per_km()
    nice = [0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 50]
    span = max([v for v in nice if v * upk <= want] or [nice[0]])
    w = span * upk
    label = f"{span:g} km" if span >= 1 else f"{span * 1000:.0f} m"
    return (f'<g><path d="M {x} {y} h {w:.1f}" stroke="{FAINT}" stroke-width="2"/>'
            f'<path d="M {x} {y - 4} v 8 M {x + w:.1f} {y - 4} v 8" '
            f'stroke="{FAINT}" stroke-width="2"/>'
            f'<text x="{x + w + 8:.1f}" y="{y + 4}" class="rc-tick">{label}</text></g>')


def salish_land(rect):
    """Land polygons from the Salish coastline cache, when the frame is in it.

    Puget Sound is not a polygon in OpenStreetMap; it is an open coastline with
    the sea on one side, so there is nothing to fill and the Waterfront panel
    came out with Elliott Bay the same colour as the city. The Salish build
    already keeps a coastline cache for 46.8–49.2°N and already knows how to sew
    an open coast into land rings inside a frame, so a Puget Sound panel starts
    as water and has the land painted onto it. A frame outside that cache, or one
    with no coast in it at all, starts as land.
    """
    w, s, e, n = rect
    if not (-124.9 < w and e < -120.5 and 46.8 < s and n < 49.16):
        return []
    try:
        land, _holes = SG.land_rings(rect)
    except SystemExit:
        return []
    return land


def basemap(race: dict, proj: Proj, rect, pw: float) -> list[str]:
    key = race["key"]
    land = salish_land(rect)
    base = WATER if land else BG
    out = [f'<rect x="0" y="0" width="{pw:.0f}" height="{VB_H:.0f}" fill="{base}"/>']
    if land:
        d = path_d(land, proj, 0.6)
        out.append(f'<path d="{d}" fill="{BG}"/>')
        out.append(f'<path d="{d}" fill="none" stroke="{WATER_EDGE}" '
                   f'stroke-width="1.6"/>')
    out += areas_on(load(key, "green"), proj, rect, GREEN, eps=1.0)
    out += areas_on([e for e in load(key, "water")
                     if e.get("tags", {}).get("natural") != "coastline"],
                    proj, rect, WATER, WATER_EDGE, eps=0.8)
    out += lines_on([way_coords(e) for e in load(key, "rail")], proj, rect,
                    f'fill="none" stroke="{RAIL_LINE}" stroke-width="1.2" '
                    f'stroke-dasharray="7 5"')
    out += lines_on(path_chains(key), proj, rect,
                    f'fill="none" stroke="{PATH}" stroke-width="1.2" '
                    f'stroke-linecap="round"')
    roads = road_chains(key)
    for w in sorted(roads):
        colour = ROAD_MAJOR if w >= 1.7 else ROAD_MINOR
        out += lines_on(roads[w], proj, rect,
                        f'fill="none" stroke="{colour}" stroke-width="{w:.1f}" '
                        f'stroke-linecap="round" stroke-linejoin="round"')
    return out


def course_markup(race: dict, pts, proj: Proj) -> list[str]:
    """The course itself: a glow, the line, the kilometre beads, the two pins."""
    accent = race["accent"]
    xy = rdp([proj(p[1], p[0]) for p in pts], 0.35)
    d = points_d(xy, False)
    out = [f'<path d="{d}" fill="none" stroke="{accent}" stroke-width="16" '
           f'stroke-opacity="0.14" stroke-linecap="round" stroke-linejoin="round"/>',
           f'<path d="{d}" fill="none" stroke="{accent}" stroke-width="5" '
           f'stroke-linecap="round" stroke-linejoin="round"/>']

    # Kilometre beads. An out-and-back lays its return over its outward leg, so
    # the beads are the only thing on the line that says which way round it went.
    cum = cumulative(pts)
    total = cum[-1]
    step = 1.0 if total >= 4 else 0.4
    marks = []
    nxt = step
    for i in range(1, len(pts)):
        if cum[i] >= nxt and nxt < total - step * 0.35:
            x, y = proj(pts[i][1], pts[i][0])
            marks.append((nxt, x, y))
            nxt += step
    for at, x, y in marks:
        lab = f"{at:g}" if step >= 1 else f"{at:.1f}"
        out.append(f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="8.5" fill="{BG}" '
                   f'fill-opacity="0.85" stroke="{accent}" stroke-width="1.6"/>'
                   f'<text x="{x:.1f}" y="{y + 3.2:.1f}" class="rc-bead">{lab}</text></g>')

    sx, sy = proj(pts[0][1], pts[0][0])
    fx, fy = proj(pts[-1][1], pts[-1][0])
    # 150 m apart or less is one place: every loop course's trace opens and
    # closes a few metres apart, and two pins on the same corner read as an error.
    same = km(pts[0][:2], pts[-1][:2]) < 0.15
    out.append(pin(sx, sy, accent, "START" if not same else "", filled=False))
    if not same:
        # A loop that opens and closes on the same block still needs two labels,
        # and one above each pin collides. The finish's goes below when they are
        # inside 70 units of each other.
        below = math.hypot(sx - fx, sy - fy) < 70
        out.append(pin(fx, fy, accent, "FINISH", filled=True, below=below))
    else:
        out.append(f'<text x="{sx:.1f}" y="{sy - 26:.1f}" class="rc-pin-label" '
                   f'text-anchor="middle">START · FINISH</text>')
    return out


def pin(x: float, y: float, accent: str, label: str, filled: bool,
        below: bool = False) -> str:
    body = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9.5" fill="{accent}" '
            f'stroke="{BG}" stroke-width="2.5"/>'
            if filled else
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9.5" fill="{BG}" '
            f'stroke="{accent}" stroke-width="4"/>')
    ly = y + 32 if below else y - 26
    text = (f'<text x="{x:.1f}" y="{ly:.1f}" class="rc-pin-label" '
            f'text-anchor="middle">{label}</text>') if label else ""
    return (f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="19" fill="{accent}" '
            f'fill-opacity="0.16"/>{body}{text}</g>')


def named_marks(race: dict, proj: Proj, rect, pw: float) -> list[str]:
    out = []
    for label, lat, lon in race.get("route", {}).get("marks", []):
        if label in ("START", "FINISH"):
            continue
        x, y = proj(lon, lat)
        if not (6 < x < pw - 6 and 6 < y < VB_H - 6):
            continue
        out.append(f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{INK}"/>'
                   f'<text x="{x:.1f}" y="{y - 12:.1f}" class="rc-place" '
                   f'text-anchor="middle">{label}</text></g>')
    return out


# ------------------------------------------------------------------- the type

MONTH = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def pretty_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{MONTH[int(m) - 1]} {int(d)} ’{y[2:]}"


def wrap_to(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if len(trial) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def title_place(xy, marks, pw: float) -> tuple[str, str]:
    """Which corner the type goes in: the one with least under it that matters.

    Four candidates. What is weighed is the labelled things first - the start and
    finish pins and any named turn, at twelve points each, because covering the
    word START is the one mistake here that loses information - then the course
    line itself at one point, then a small penalty on the bottom two so that a
    title sits above its subject when both are equally free. Streets and parks are
    not weighed at all: they are ground, and the scrim is meant to sit on them.
    """
    bw = block_w(pw)
    spots = [("top", "left", 0.0, HEADER_CLEAR),
             ("top", "right", pw - bw - PAD, HEADER_CLEAR),
             ("bottom", "left", 0.0, VB_H - BLOCK_H - 96),
             ("bottom", "right", pw - bw - PAD, VB_H - BLOCK_H - 96)]
    best, best_cost = ("top", "left"), None
    for vside, side, x0, y0 in spots:
        def inside(pts, grow=0.0):
            return sum(1 for x, y in pts
                       if x0 - grow <= x <= x0 + bw + PAD + grow
                       and y0 - grow <= y <= y0 + BLOCK_H + PAD + grow)
        # 40 units of grow for the marks: a pin's label is set above it.
        # The course counts as the share of it that falls under the block, not as
        # a number of points: a course is traced at whatever density its source
        # published, and a raw count let a dense line outvote a start pin.
        share = inside(xy) / max(1, len(xy))
        cost = 12 * inside(marks, 40.0) + 8 * share + (0 if vside == "top" else 1)
        if best_cost is None or cost < best_cost:
            best, best_cost = (vside, side), cost
    return best


def block_w(pw: float) -> float:
    """How wide the type block may be: the panel, less its margins."""
    return min(660.0, pw - 2 * PAD)


def title_block(race: dict, xy, marks, pw: float) -> str:
    """The name, the date and the place, set on the map in one corner.

    Two lines of information and nothing else. It carried a distance ring, three
    metric tiles, an elevation profile, a paragraph of prose and a provenance
    line at various points; all of it was caption competing with the drawing, and
    the drawing already says how far it went, because the course is beaded at
    every kilometre. Provenance lives on the course's entry in
    scripts/race_courses.py, and the OpenStreetMap credit stays on the map
    because the licence asks for it there.

    A scrim goes under it: on a dark ground light type reads on its own, but the
    ground here is a real city and its parks are pale enough to swallow a letter.
    """
    accent = race["accent"]
    vside, side = title_place(xy, marks, pw)
    bw = block_w(pw)
    x = PAD if side == "left" else pw - PAD
    anchor = "start" if side == "left" else "end"
    gx = 0.0 if side == "left" else pw - bw - PAD
    top = HEADER_CLEAR if vside == "top" else VB_H - BLOCK_H - 96
    # The corner is the best of four, which on a narrow panel can still be a
    # corner with something in it. Say so rather than shipping a covered pin.
    hit = [1 for mx, my in marks
           if gx - 40 <= mx <= gx + bw + PAD + 40
           and top - 40 <= my <= top + BLOCK_H + PAD + 40]
    print(f"    title {vside} {side}" + (f", {len(hit)} mark(s) under it" if hit else ""))
    # The scrim runs to the panel edge behind the block, so the type never sits
    # on a visible slab: only the gradient's own fade has an edge.
    sy = 0.0 if vside == "top" else top
    sh = top + BLOCK_H + PAD if vside == "top" else VB_H - top
    out = [f'<rect x="{gx:.0f}" y="{sy:.0f}" width="{bw + PAD:.0f}" '
           f'height="{sh:.0f}" '
           f'fill="url(#rc-scrim{"" if vside == "top" else "-up"})"/>']
    y = top + 100
    # 0.56 of the size is about the width of a character at this weight.
    for line in wrap_to(race["name"], int(bw / (36 * 0.56))):
        out.append(f'<text x="{x:.0f}" y="{y:.0f}" class="rc-title" '
                   f'text-anchor="{anchor}">{line}</text>')
        y += 44
    dates = " · ".join(pretty_date(d) for d in race["dates"])
    limit = int(bw / (14 * 0.55))
    one = f"{dates}  ·  {place_of(race)}"
    if len(one) <= limit:
        out.append(f'<text x="{x:.0f}" y="{y + 4:.0f}" class="rc-meta" '
                   f'text-anchor="{anchor}">'
                   f'<tspan fill="{accent}">{dates}</tspan>'
                   f'<tspan fill="{DIM}">  ·  {place_of(race)}</tspan></text>')
    else:
        for line, colour in ([(dates, accent)]
                             + [(l, DIM) for l in wrap_to(place_of(race), limit)]):
            out.append(f'<text x="{x:.0f}" y="{y + 4:.0f}" class="rc-meta" '
                       f'text-anchor="{anchor}" fill="{colour}">{line}</text>')
            y += 21
    if race.get("glyph"):
        gx2 = x + 20 if side == "left" else x - 20
        out.append(f'<use href="#{race["glyph"]}" '
                   f'transform="translate({gx2:.0f}, {top + 54:.0f}) scale(1.5)"/>')
    return "".join(out)


def place_of(race: dict) -> str:
    return f'{race["venue"]} · {race["city"]}'


# ------------------------------------------------------------------ one panel

def build_panel(race: dict, n: int, total: int) -> str:
    print(f"panel {n} {race['key']}")
    pw = panel_width(race)
    frame = frame_for_panel(race, pw)
    proj = Proj(frame[0], frame[1], frame[2], frame[3], MAP_X, 0, pw, VB_H)
    print(f"    {pw:.0f} x {VB_H:.0f} paper, {proj.px_per_km():.1f} units/km, "
          f"frame {tuple(round(v, 4) for v in frame)}")
    rect = frame

    body = basemap(race, proj, rect, pw)
    pts = course_of(race)
    xy = [proj(p[1], p[0]) for p in pts]
    # The things that carry a word: the two pins and any named turn.
    marks = ([xy[0], xy[-1]] if xy else []) + [
        proj(lon, lat) for label, lat, lon in race.get("route", {}).get("marks", [])
        if label not in ("START", "FINISH")]
    if pts:
        body += course_markup(race, pts, proj)
        body += named_marks(race, proj, rect, pw)
    body.append(scale_bar(PAD, VB_H - 46, proj))
    body.append(f'<text x="{pw - PAD:.0f}" y="{VB_H - 42:.0f}" class="rc-src" '
                f'text-anchor="end">Streets, water and parks: OpenStreetMap</text>')

    label = (f'{race["name"]}: {race["sub"]}, '
             f'{" and ".join(pretty_date(d) for d in race["dates"])}')
    return (f'<svg class="rc-panel sg-sheet" id="rc-panel-{race["key"]}" '
            f'viewBox="0 0 {pw:.0f} {VB_H:.0f}" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{label}">'
            f'<defs>{{DEFS}}</defs>'
            f'<g clip-path="url(#rc-map-clip-{race["key"]})">{"".join(body)}'
            f'{title_block(race, xy, marks, pw)}</g></svg>')


# --------------------------------------------------------------------- assembly

def race_defs() -> str:
    """The event marks. Kept here, not lifted from the page.

    They used to live in the old chart's <defs>, which this build replaces, and a
    generator that reads its own glyphs out of the markup it overwrites works
    exactly once. These are the same drawings, restruck for a dark panel: a thin
    light stroke and one filled accent each, at about 20 units across.
    """
    return "".join(GLYPHS.values())


# A line icon each, in the panel's own ink. Roughly 20 units wide, centred.
GLYPHS = {
    # cherry blossom: five petals round a stamen
    "rc-blossom": '<g id="rc-blossom" class="rc-ic">'
        '<circle cx="0" cy="-6.4" r="4.2" fill="#e6738f" fill-opacity="0.35"/>'
        '<circle cx="6.1" cy="-2" r="4.2" fill="#e6738f" fill-opacity="0.35"/>'
        '<circle cx="3.8" cy="5.3" r="4.2" fill="#e6738f" fill-opacity="0.35"/>'
        '<circle cx="-3.8" cy="5.3" r="4.2" fill="#e6738f" fill-opacity="0.35"/>'
        '<circle cx="-6.1" cy="-2" r="4.2" fill="#e6738f" fill-opacity="0.35"/>'
        '<circle cx="0" cy="0" r="1.9" fill="#e6738f" stroke="none"/></g>',
    # pumpkin: three lobes and a stalk
    "rc-pumpkin": '<g id="rc-pumpkin" class="rc-ic">'
        '<path d="M 0 -8 C 0.6 -10.4, 1.8 -11.6, 3.6 -12.2"/>'
        '<path d="M -9 0 C -9 -5.6, -4.5 -8, 0 -8 C 4.5 -8, 9 -5.6, 9 0 '
        'C 9 5.6, 4.5 8.6, 0 8.6 C -4.5 8.6, -9 5.6, -9 0 Z" '
        'fill="#e08344" fill-opacity="0.3"/>'
        '<path d="M -3.4 -7.3 C -5.1 -2.3, -5.1 3.4, -3.4 7.9 '
        'M 3.4 -7.3 C 5.1 -2.3, 5.1 3.4, 3.4 7.9"/></g>',
    # beer: a stein with a head on it
    "rc-mug": '<g id="rc-mug" class="rc-ic">'
        '<path d="M 5.6 -4.6 C 10.8 -4.6, 10.8 4, 5.2 4"/>'
        '<path d="M -5.6 -8 L 5.6 -8 L 4.7 9 L -4.7 9 Z" '
        'fill="#e0a53c" fill-opacity="0.3"/>'
        '<path d="M -5.6 -8 Q -3.9 -10.8 -2 -9.1 Q 0 -12 2 -9.1 Q 3.9 -10.8 5.6 -8"/>'
        '</g>',
    # cocoa: a mug with steam
    "rc-cocoa": '<g id="rc-cocoa" class="rc-ic">'
        '<path d="M 6.8 -2.2 C 11.4 -2.2, 11.4 5.2, 6 5.2"/>'
        '<path d="M -6.8 -4.6 L 6.8 -4.6 L 5.4 9 L -5.4 9 Z" '
        'fill="#a5714f" fill-opacity="0.42"/>'
        '<path d="M -2.8 -8 q 1.4 -2.2 0 -4.6 M 2.3 -8 q 1.4 -2.2 0 -4.6"/></g>',
    # start flag
    "rc-flag": '<g id="rc-flag" class="rc-ic">'
        '<path d="M -3 9 L -3 -10"/>'
        '<path d="M -3 -10 L 8 -6.6 L -3 -3.2 Z" fill="#3f9fd6" fill-opacity="0.4"/>'
        '</g>',
    # anchor: a lake town with a marina
    "rc-anchor": '<g id="rc-anchor" class="rc-ic">'
        '<circle cx="0" cy="-7.5" r="2.2"/>'
        '<path d="M 0 -5.2 L 0 8"/><path d="M -4.8 -1.4 L 4.8 -1.4"/>'
        '<path d="M -7.5 1.4 Q -6.8 8.2 0 9 Q 6.8 8.2 7.5 1.4"/></g>',
    # Gas Works Park: the cracking towers
    "rc-gasworks": '<g id="rc-gasworks" class="rc-ic">'
        '<path d="M -9 9 L -9 -5 M -3 9 L -3 -10 M 3 9 L 3 -7 M 9 9 L 9 -2"/>'
        '<path d="M -11 9 L 11 9"/>'
        '<path d="M -9 -5 L -3 -10 M -3 -10 L 3 -7 M 3 -7 L 9 -2"/>'
        '<circle cx="-3" cy="-10" r="2" fill="#7a6fd6" fill-opacity="0.5"/></g>',
    # Tough Mudder: a wall and the wire over it
    "rc-mudder": '<g id="rc-mudder" class="rc-ic">'
        '<path d="M -10 9 L 10 9"/>'
        '<path d="M -8 9 L -8 -3 L 8 -3 L 8 9" fill="#d98b3a" fill-opacity="0.22"/>'
        '<path d="M -8 3 L 8 3"/>'
        '<path d="M -11 -7 L 11 -7"/>'
        '<path d="M -6 -9 L -6 -5 M -8 -7 L -4 -7 M 4 -9 L 4 -5 M 2 -7 L 6 -7"/></g>',
    # Boston: the unicorn, as the B.A.A. draws it: a head and a horn
    "rc-unicorn": '<g id="rc-unicorn" class="rc-ic">'
        '<path d="M -7 9 C -8 3, -6 -2, -1 -5 C 2 -6.6, 5 -6.2, 7 -4.4 '
        'C 8.6 -3, 8.4 -0.6, 6.4 0.6 L 1 3.6 C -1.6 5, -2.6 6.8, -2.6 9 Z" '
        'fill="#f0c23c" fill-opacity="0.3"/>'
        '<path d="M 1 -5.6 L 4.6 -12.6"/>'
        '<path d="M -3.6 -3.6 C -6 -6.6, -6.6 -9.6, -5.6 -12.4"/>'
        '<circle cx="3.2" cy="-2.6" r="1" fill="#f0c23c" stroke="none"/></g>',
}


def subset_defs(race: dict, markup: str) -> str:
    used = set(re.findall(r'href="#(rc-[a-z-]+)"', markup))
    pw = re.search(r'viewBox="0 0 (\d+)', markup).group(1)
    clip = (f'<clipPath id="rc-map-clip-{race["key"]}"><rect x="0" y="0" '
            f'width="{pw}" height="{VB_H:.0f}"/></clipPath>')
    # The scrim under the type: the panel's own ground, fading out away from the
    # edge it sits on. A gradient and not a panel, so it has no edge to line
    # anything up against.
    scrim = ('<linearGradient id="rc-scrim" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BG}" stop-opacity="0.9"/>'
             f'<stop offset="0.62" stop-color="{BG}" stop-opacity="0.62"/>'
             f'<stop offset="1" stop-color="{BG}" stop-opacity="0"/>'
             '</linearGradient>'
             '<linearGradient id="rc-scrim-up" x1="0" y1="1" x2="0" y2="0">'
             f'<stop offset="0" stop-color="{BG}" stop-opacity="0.9"/>'
             f'<stop offset="0.62" stop-color="{BG}" stop-opacity="0.62"/>'
             f'<stop offset="1" stop-color="{BG}" stop-opacity="0"/>'
             '</linearGradient>')
    return "".join(v for k, v in GLYPHS.items() if k in used) + clip + scrim


def section_html(panels: list[str]) -> str:
    slides = "".join(f'<div class="sg-slide">{p}</div>' for p in panels)
    return f'''{BEGIN}
    <!-- Every start line, one panel each, on the real ground it was run over.
         Generated: edit scripts/race_courses.py and rebuild, never this markup.
         The courses are the organisers' own published lines; the streets, water
         and parks under them are OpenStreetMap. -->
    <section id="race-routes" aria-hidden="true" aria-label="Race routes">
        <button class="back-to-globe sg-up" type="button" data-target="pnw-section">
            <span aria-hidden="true">↑</span> Charts
        </button>
        <button class="sg-nav prev" type="button" aria-label="Previous race" disabled>
            <span aria-hidden="true">‹</span>
        </button>
        <button class="sg-nav next" type="button" aria-label="Next race">
            <span aria-hidden="true">›</span>
        </button>
        <div class="sg-pager rc-pager" id="rcPager">{slides}</div>
        <div class="sg-dots rc-dots" id="rcDots" role="tablist" aria-label="Races"></div>
    </section>
    {END}'''


def main() -> int:
    html = MAPS.read_text()
    print(f"glyphs: {len(GLYPHS)}")

    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")

    built = []
    for i, race in enumerate(R.RACES, 1):
        if only and race["key"] not in only:
            continue
        svg = build_panel(race, i, len(R.RACES))
        svg = svg.replace("{DEFS}", subset_defs(race, svg))
        print(f"    {len(svg) // 1024} KB")
        built.append(svg)

    style = re.search(r"<style>(.*?)</style>", html, re.S)
    head = ("<!doctype html><meta charset=utf-8><style>"
            + (style.group(1) if style else "")
            + "html,body{margin:0;height:100%;background:#0e1216}"
            + "#race-routes{opacity:1;transform:none}"
            + ".sg-pager{scroll-snap-type:none}</style>")
    Path("/tmp/race_preview.html").write_text(
        head + '<section id="race-routes"><div class="sg-pager">'
        + "".join(f'<div class="sg-slide">{s}</div>' for s in built)
        + "</div></section>")
    for i, svg in enumerate(built, 1):
        Path(f"/tmp/race_panel{i}.html").write_text(
            head.replace("</style>", "svg{display:block;width:100vw;height:100vh}</style>")
            + svg)
    print("preview /tmp/race_preview.html  and /tmp/race_panel1.html ...")

    if "--preview" in sys.argv or only:
        return 0
    if BEGIN not in html:
        raise SystemExit("race panel markers not found in maps.html")
    html = re.sub(re.escape(BEGIN) + ".*?" + re.escape(END),
                  lambda _m: section_html(built), html, flags=re.S)
    MAPS.write_text(html)
    print(f"wrote   {MAPS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
