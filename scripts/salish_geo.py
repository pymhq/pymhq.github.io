"""Geometry engine for the to-scale Salish Sea chart (panel 2.5 of maps.html).

Panel 2 is drawn by hand: every coast is an invented curve, and the places sit
where the composition wanted them, not where they are. This module does the
opposite job: it turns the OpenStreetMap data cached by fetch_salish_geo.py
into SVG paths under one honest projection, so the shapes and the distances on
panel 2.5 are the real ones.

What lives here is only geometry: projection, coastline assembly, clipping,
simplification. The drawing itself, which doodle goes where, what gets a
label, is build_salish_geo_panel.py.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

CACHE = Path.home() / ".cache" / "pengandy-salish-geo"

# The frame the data was fetched for; see fetch_salish_geo.py.
DATA_S, DATA_W, DATA_N, DATA_E = 46.80, -124.90, 49.16, -120.50


# ---------------------------------------------------------------- projection

def merc_y(lat: float) -> float:
    """Web Mercator y, in radians of longitude, north positive."""
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def merc_x(lon: float) -> float:
    return math.radians(lon)


@dataclass
class Proj:
    """A Mercator window: one geographic box onto one SVG rectangle.

    Uniform scale in x and y, which is what makes the drawing to scale: an
    inset is the same projection at a larger scale, never a stretched one.
    """

    west: float
    south: float
    east: float
    north: float
    x0: float
    y0: float
    width: float
    height: float

    def __post_init__(self) -> None:
        self.mx0, self.mx1 = merc_x(self.west), merc_x(self.east)
        self.my0, self.my1 = merc_y(self.south), merc_y(self.north)
        sx = self.width / (self.mx1 - self.mx0)
        sy = self.height / (self.my1 - self.my0)
        # One scale for both axes: fit, then centre the slack.
        self.k = min(sx, sy)
        self.pad_x = (self.width - (self.mx1 - self.mx0) * self.k) / 2
        self.pad_y = (self.height - (self.my1 - self.my0) * self.k) / 2

    def inverse(self, x: float, y: float):
        """Sheet units back to (lat, lon).

        Needed to ask what a nudged glyph is now standing on: a 26-unit nudge is
        840 m on the Seattle sheet, enough to walk a statue into the Sound.
        """
        mx = (x - self.x0 - self.pad_x) / self.k + self.mx0
        my = self.my1 - (y - self.y0 - self.pad_y) / self.k
        lon = math.degrees(mx)
        lat = math.degrees(2 * math.atan(math.exp(my)) - math.pi / 2)
        return lat, lon

    @classmethod
    def fit_width(cls, west, south, east, north, x0, y0, width) -> "Proj":
        """The box at a given width, with the height the projection asks for."""
        h = width * (merc_y(north) - merc_y(south)) / (merc_x(east) - merc_x(west))
        return cls(west, south, east, north, x0, y0, width, h)

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        x = self.x0 + self.pad_x + (merc_x(lon) - self.mx0) * self.k
        y = self.y0 + self.pad_y + (self.my1 - merc_y(lat)) * self.k
        return x, y

    def px_per_km(self, lat: float | None = None) -> float:
        lat = self.north / 2 + self.south / 2 if lat is None else lat
        # 1 km of ground at this latitude, in projected units.
        deg = 1.0 / (111.320 * math.cos(math.radians(lat)))
        return math.radians(deg) * self.k

    @property
    def box(self) -> tuple[float, float, float, float]:
        return (self.x0 + self.pad_x, self.y0 + self.pad_y,
                (self.mx1 - self.mx0) * self.k, (self.my1 - self.my0) * self.k)


# ------------------------------------------------------------------- loading

def load(layer: str) -> list[dict]:
    path = CACHE / f"{layer}.json"
    if not path.exists():
        raise SystemExit(f"missing {path}; run scripts/fetch_salish_geo.py")
    return json.loads(path.read_text())["elements"]


def way_coords(el: dict) -> list[tuple[float, float]]:
    """(lon, lat) list for an Overpass `out geom` way."""
    return [(p["lon"], p["lat"]) for p in el.get("geometry", []) if p]


# -------------------------------------------------------- coastline assembly

def stitch(ways: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Join ways that share an endpoint into the longest chains possible.

    OSM coastline arrives as thousands of fragments in no order, all drawn
    with the land on the left. Joined end to end they become either a closed
    ring (an island) or a chain that runs off the edge of the frame.
    """
    ends: dict[tuple[float, float], list[int]] = {}
    chains = [list(w) for w in ways if len(w) > 1]
    for i, ch in enumerate(chains):
        ends.setdefault(ch[0], []).append(i)
        ends.setdefault(ch[-1], []).append(i)

    used = [False] * len(chains)
    out: list[list[tuple[float, float]]] = []

    def pop_at(pt, exclude):
        for j in ends.get(pt, []):
            if not used[j] and j != exclude:
                return j
        return None

    for i, ch in enumerate(chains):
        if used[i]:
            continue
        used[i] = True
        cur = list(ch)
        # forward
        while True:
            j = pop_at(cur[-1], i)
            if j is None:
                break
            used[j] = True
            nxt = chains[j]
            cur += (nxt[1:] if nxt[0] == cur[-1] else list(reversed(nxt))[1:])
            if cur[0] == cur[-1]:
                break
        # backward
        while cur[0] != cur[-1]:
            j = pop_at(cur[0], i)
            if j is None:
                break
            used[j] = True
            nxt = chains[j]
            cur = (nxt[:-1] if nxt[-1] == cur[0] else list(reversed(nxt))[:-1]) + cur
        out.append(cur)
    return out


def _inside(pt, rect) -> bool:
    w, s, e, n = rect
    return w <= pt[0] <= e and s <= pt[1] <= n


def _cross(a, b, rect):
    """Where segment a->b crosses the rect edge, entering or leaving."""
    w, s, e, n = rect
    (x1, y1), (x2, y2) = a, b
    hits = []
    if x1 != x2:
        for bx in (w, e):
            t = (bx - x1) / (x2 - x1)
            if 0 <= t <= 1:
                y = y1 + t * (y2 - y1)
                if s <= y <= n:
                    hits.append((t, (bx, y)))
    if y1 != y2:
        for by in (s, n):
            t = (by - y1) / (y2 - y1)
            if 0 <= t <= 1:
                x = x1 + t * (x2 - x1)
                if w <= x <= e:
                    hits.append((t, (x, by)))
    hits.sort()
    return [h[1] for h in hits]


def clip_chain(chain, rect) -> list[list[tuple[float, float]]]:
    """Split a polyline into the pieces that lie inside rect."""
    pieces, cur = [], []
    for a, b in zip(chain, chain[1:]):
        ain, bin_ = _inside(a, rect), _inside(b, rect)
        if ain:
            if not cur:
                cur = [a]
            else:
                cur.append(a)
        xs = _cross(a, b, rect)
        if ain and not bin_:
            if xs:
                cur.append(xs[-1])
            pieces.append(cur)
            cur = []
        elif not ain and bin_:
            cur = [xs[0]] if xs else []
        elif not ain and not bin_ and len(xs) >= 2:
            pieces.append([xs[0], xs[-1]])
    if cur:
        if _inside(chain[-1], rect):
            cur.append(chain[-1])
        pieces.append(cur)
    return [p for p in pieces if len(p) > 1]


def _on_edge(pt, rect, tol: float = 1e-7) -> bool:
    """Is this point actually on the frame? `_perimeter_t` assumes it is.

    Its last branch returns a west-edge position for anything that reached it,
    so an interior point silently parameterises as being on the west edge.
    """
    w, s, e, n = rect
    x, y = pt
    return (abs(y - s) < tol or abs(x - e) < tol
            or abs(y - n) < tol or abs(x - w) < tol)


def _perimeter_t(pt, rect) -> float:
    """Position of a boundary point along the rect, counter-clockwise from SW.

    Counter-clockwise in lon/lat (y north): south edge west to east, then east
    edge, then north edge, then west edge. Coastline keeps land on the left, so
    walking on in this direction from where a chain leaves the frame is walking
    over land, which is exactly how the ring gets closed.
    """
    w, s, e, n = rect
    x, y = pt
    eps = 1e-9
    if abs(y - s) < eps:
        return 0 + (x - w) / (e - w)
    if abs(x - e) < eps:
        return 1 + (y - s) / (n - s)
    if abs(y - n) < eps:
        return 2 + (e - x) / (e - w)
    return 3 + (n - y) / (n - s)


def _corner_points(t_from, t_to, rect):
    """The rect corners passed walking counter-clockwise from t_from to t_to."""
    w, s, e, n = rect
    corners = {1: (e, s), 2: (e, n), 3: (w, n), 0: (w, s)}
    out, t = [], math.floor(t_from) + 1
    span = (t_to - t_from) % 4
    while (t - t_from) % 4 <= span and len(out) < 5:
        out.append(corners[int(t) % 4])
        t += 1
    return out


def _rotate_outside(ring, rect):
    """Re-start a closed ring at a node outside rect.

    A ring is a cycle, so where its node list happens to begin is arbitrary.
    Clipping it while it begins *inside* the frame cuts it at that node, and the
    one boundary-to-boundary piece comes back as two pieces meeting at a point
    in the middle of the map. `_perimeter_t` then reads that interior point as
    lying on the west edge, and the ring closes with a straight chord across the
    frame: this is what drew the Olympic Peninsula as open water.
    """
    body = ring[:-1] if ring[0] == ring[-1] else list(ring)
    for k, pt in enumerate(body):
        if not _inside(pt, rect):
            return body[k:] + body[:k] + [body[k]]
    return ring


def _join_open(pieces):
    """Join pieces that meet head-to-tail at a shared node."""
    by_start: dict[tuple[float, float], list] = {}
    for p in pieces:
        by_start.setdefault(p[0], []).append(p)
    out, seen = [], set()
    for p in pieces:
        if id(p) in seen:
            continue
        cur = list(p)
        seen.add(id(p))
        while True:
            nxt = next((q for q in by_start.get(cur[-1], [])
                        if id(q) not in seen), None)
            if nxt is None or cur[0] == cur[-1]:
                break
            seen.add(id(nxt))
            cur += nxt[1:]
        out.append(cur)
    return out


_STITCHED: list = []
_LAND_CACHE: dict = {}


def coast_chains():
    """The stitched coastline, once. Stitching it is the build's single biggest
    cost and it does not depend on the frame."""
    if not _STITCHED:
        _STITCHED.extend(stitch([way_coords(el) for el in load("coastline")]))
    return _STITCHED


_ISLANDS: list = []


def island_rings() -> list[list]:
    """One ring per island, as OpenStreetMap draws it: closed, whole, unclipped.

    `land_rings` answers a different question - what land is in this frame - and
    to answer it it closes the open mainland coast against the frame edge, which
    can walk past an island and join it to the run. That is fine for a fill and
    useless for a colour: an island's colour is a fact about the island, not
    about the sheet it turns up on. The coastline layer already carries every
    island as its own closed way, so this is that list, straight.
    """
    if not _ISLANDS:
        _ISLANDS.extend(ch for ch in coast_chains()
                        if len(ch) > 3 and ch[0] == ch[-1] and _signed_area(ch) > 0)
    return _ISLANDS


def _sew_open(pieces, rect, tol=0.02):
    """Bridge coastline pieces that stop in open country.

    OSM hands the coastline over to riverbank at the head of an inlet, so a piece
    can end inland. Dropping those pieces breaks the chain the frame-closing
    needs, and the mainland then never closes into a ring: widening the frame west
    to the Pacific did exactly that, and the whole of Washington rendered as open
    water. Ends within `tol` degrees of each other are sewn together.
    """
    out = [list(p) for p in pieces]
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(out):
            if not a or _on_edge(a[-1], rect):
                continue
            best, bj, brev = tol, None, False
            for j, b in enumerate(out):
                if i == j or not b:
                    continue
                for rev in (False, True):
                    end = b[-1] if rev else b[0]
                    d = math.hypot(a[-1][0] - end[0], a[-1][1] - end[1])
                    if d < best:
                        best, bj, brev = d, j, rev
            if bj is not None:
                piece = out[bj][::-1] if brev else out[bj]
                out[i] = a + piece
                out[bj] = []
                changed = True
                break
    return [p for p in out if len(p) > 1]


def land_rings(rect) -> tuple[list[list], list[list]]:
    """Land polygons and lake-like holes inside rect, from the coastline layer.

    Returns (land, holes) as lon/lat rings. Cached per frame: seven sheets, a
    water grid and three checkers all ask for the same handful of frames.
    """
    if rect in _LAND_CACHE:
        return _LAND_CACHE[rect]
    chains = coast_chains()
    closed, open_ = [], []
    for ch in chains:
        if ch[0] == ch[-1]:
            if all(_inside(p, rect) for p in ch):
                closed.append(ch)
                continue
            for piece in clip_chain(_rotate_outside(ch, rect), rect):
                (closed if piece[0] == piece[-1] else open_).append(piece)
        else:
            open_ += clip_chain(ch, rect)

    land, holes = [], []
    for ring in closed:
        (land if _signed_area(ring) > 0 else holes).append(ring)

    # Close the open chains against the frame, in order around it. Only pieces
    # that start and end on the frame can be closed this way; a chain that stops
    # in open country (OSM hands the coastline over to riverbank at the head of
    # an inlet) has no place on the perimeter and is left as an unclosed edge.
    pieces = _sew_open(_join_open([p for p in open_ if len(p) > 1]), rect)
    pieces = [p for p in pieces
              if len(p) > 1 and _on_edge(p[0], rect) and _on_edge(p[-1], rect)]
    starts = sorted(range(len(pieces)), key=lambda i: _perimeter_t(pieces[i][0], rect))
    used = set()
    for i in starts:
        if i in used:
            continue
        ring, cur = [], i
        while cur is not None and cur not in used:
            used.add(cur)
            ring += pieces[cur]
            t_end = _perimeter_t(pieces[cur][-1], rect)
            nxt, best = None, 5.0
            for j in starts:
                if j in used:
                    continue
                d = (_perimeter_t(pieces[j][0], rect) - t_end) % 4
                if d < best:
                    best, nxt = d, j
            t_start = _perimeter_t(pieces[i][0], rect)
            d_close = (t_start - t_end) % 4
            if nxt is None or d_close <= best:
                ring += _corner_points(t_end, t_start, rect)
                break
            ring += _corner_points(t_end, _perimeter_t(pieces[nxt][0], rect), rect)
            cur = nxt
        if len(ring) > 3:
            land.append(ring)
    _LAND_CACHE[rect] = (land, holes)
    return land, holes


def on_land(pt, limit: float = 0.6) -> bool:
    """Is this point on the land side of the nearest coastline?

    A frame can be small enough to hold no coastline at all. Meydenbauer Bay is
    2 km of Bellevue on a lake shore, 8 km from salt water, so it has no coast
    ring and the sheet painted the whole pane in the water colour: the town read
    as open sea. OSM draws the coastline with land on the left, so the side of
    the nearest segment answers it.
    """
    x0, y0 = pt
    best, side = None, False
    span = 0.05
    while span <= limit:
        for chain in coast_chains():
            for a, b in zip(chain, chain[1:]):
                if (max(a[0], b[0]) < x0 - span or min(a[0], b[0]) > x0 + span
                        or max(a[1], b[1]) < y0 - span
                        or min(a[1], b[1]) > y0 + span):
                    continue
                # metric-ish: longitude shrinks with latitude
                k = math.cos(math.radians(y0))
                ax, ay = (a[0] - x0) * k, a[1] - y0
                bx, by = (b[0] - x0) * k, b[1] - y0
                dx, dy = bx - ax, by - ay
                seg = dx * dx + dy * dy
                t = 0.0 if seg == 0 else max(0.0, min(1.0,
                                                      -(ax * dx + ay * dy) / seg))
                px, py = ax + dx * t, ay + dy * t
                d = px * px + py * py
                if best is None or d < best:
                    best = d
                    side = (dx * (0 - ay) - dy * (0 - ax)) > 0
        if best is not None:
            return side
        span *= 3
    # No coastline within `limit` degrees. Every body of salt water in this
    # region is narrower than that, so a point this far from any coast is
    # inland: the North Cascades are 130 km from the sea and were being called
    # open water.
    return True


def _lake_rings_near(pt, span=0.2):
    """Lakes within span degrees of a point, each as (outline, holes).

    Handles relations as well as ways: Lake Washington and Lake Union both come
    back as multipolygons, so a ways-only test finds neither. The holes come back
    with them because a lake's holes are islands: Mercer Island is an inner ring
    of Lake Washington and not a piece of coast, so an outline-only test calls
    the whole island water and puts every drawing on it in the lake.
    """
    x0, y0 = pt
    s, w, n, e = y0 - span, x0 - span, y0 + span, x0 + span
    out = []
    for el in load("water"):
        b = el.get("bounds")
        if b and (b["maxlat"] < s or b["minlat"] > n
                  or b["maxlon"] < w or b["minlon"] > e):
            continue
        if el["type"] == "way":
            rings, holes = [way_coords(el)], []
        else:
            ways = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                    for m in el.get("members", []) if m.get("role") in ("outer", "")]
            rings = [r for r in stitch([x for x in ways if len(x) > 1])
                     if len(r) > 3 and r[0] == r[-1]]
            iways = [[(p["lon"], p["lat"]) for p in m.get("geometry", [])]
                     for m in el.get("members", []) if m.get("role") == "inner"]
            holes = [r for r in stitch([x for x in iways if len(x) > 1])
                     if len(r) > 3 and r[0] == r[-1]]
        out += [(r, holes) for r in rings if len(r) > 3]
    return out


def in_ring(pt, ring) -> bool:
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
            c = not c
    return c


_NEAR_LAND: dict = {}


def land_side(pt, span: float = 0.08):
    """Is this point inside the land the sheets actually draw? None if unknown.

    `on_land` answers by the side of the nearest coastline segment, which is cheap
    and right in open country and wrong exactly where a shoreline doubles back on
    itself. At Alki the nearest segment to a point in Elliott Bay is a piece of
    the Duwamish Head shore running the other way, so the bay came back as land:
    the Statue of Liberty was snapped 360 m further out to sea to "put it ashore",
    and the checker that is supposed to catch that agreed with the snap, because
    both asked the same wrong question.

    This asks the question the drawing answers: the same land_rings the sheet
    fills, for a small frame round the point. Cached per 0.08 degree cell, which
    is about 9 km, so a sheet's worth of glyphs shares a handful of frames.
    """
    lo, la = pt
    key = (int(math.floor(lo / span)), int(math.floor(la / span)))
    if key not in _NEAR_LAND:
        rect = (key[0] * span - span, key[1] * span - span,
                key[0] * span + 2 * span, key[1] * span + 2 * span)
        try:
            land, _holes = land_rings(rect)
        except (SystemExit, ValueError, ZeroDivisionError):
            land = []
        _NEAR_LAND[key] = land
    rings = _NEAR_LAND[key]
    if not rings:
        return None
    return any(in_ring(pt, r) for r in rings)


def is_dry(pt) -> bool:
    """Dry land: inside the drawn coastline, and not inside a lake.

    The coastline test alone answers the sea only, so it calls the middle of Lake
    Union land. Gas Works Park sits on that lake's north shore and Waverly Beach
    on Lake Washington's, so telling their doodles from the water needs the lakes
    too. A lake's own islands are dry: Mercer Island is a hole in Lake Washington,
    so the pâtisserie in its town centre is on land and not 1.5 km out in a lake.
    """
    side = land_side(pt)
    if side is None:
        side = on_land(pt)
    if not side:
        return False
    return not any(in_ring(pt, r) and not any(in_ring(pt, h) for h in holes)
                   for r, holes in _lake_rings_near(pt))


def snap_to(pt, want_dry: bool, max_m: float = 500.0):
    """Nudge a point the shortest way onto land, or into the water.

    A beach, a waterfront park and a marina all have coordinates on the
    waterline, and a 20-unit glyph centred on the waterline reads as floating:
    Alki's Statue of Liberty was standing in Puget Sound. This moves the drawing
    to the side the thing is actually on, and reports how far it went so the
    move can be audited rather than trusted.
    """
    if is_dry(pt) == want_dry:
        return pt, 0.0
    x0, y0 = pt
    k = math.cos(math.radians(y0))
    best = None
    step = 40.0
    while step <= max_m:
        for i in range(24):
            a = 2 * math.pi * i / 24
            dx = step * math.cos(a) / 111320.0 / k
            dy = step * math.sin(a) / 110900.0
            cand = (x0 + dx, y0 + dy)
            if is_dry(cand) == want_dry:
                best = (cand, step)
                break
        if best:
            return best
        step += 40.0
    return pt, -1.0


class WaterGrid:
    """A water mask over a frame, and A* across it.

    A ferry track drawn as a straight line between two slips crosses whatever is
    in the way: Anacortes to Friday Harbor put 111 of 273 sample points on dry
    land, through Decatur, Lopez and Shaw. Hand-placed waypoints only move the
    problem, so the track is routed instead, over a mask built by scanline-
    filling the coastline rings.
    """

    _cache: dict = {}

    def __init__(self, rect, step=0.0030):
        self.rect, self.step = rect, step
        w, s, e, n = rect
        self.nx = int((e - w) / step) + 2
        self.ny = int((n - s) / step) + 2
        land, _ = land_rings(rect)
        edges = []
        for ring in land:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if a[1] != b[1]:
                    edges.append((a, b))
        self.mask = bytearray(self.nx * self.ny)
        for j in range(self.ny):
            lat = s + j * step
            xs = []
            for (x1, y1), (x2, y2) in edges:
                if (y1 > lat) != (y2 > lat):
                    xs.append(x1 + (lat - y1) / (y2 - y1) * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                i0 = max(0, int((xs[k] - w) / step) + 1)
                i1 = min(self.nx - 1, int((xs[k + 1] - w) / step))
                row = j * self.nx
                for i in range(i0, i1 + 1):
                    self.mask[row + i] = 1

    @classmethod
    def shared(cls, rect, step=0.0030):
        key = (rect, step)
        if key not in cls._cache:
            cls._cache[key] = cls(rect, step)
        return cls._cache[key]

    def cell(self, lat, lon):
        w, s, e, n = self.rect
        return (min(max(int((lon - w) / self.step), 0), self.nx - 1),
                min(max(int((lat - s) / self.step), 0), self.ny - 1))

    def pos(self, i, j):
        w, s, e, n = self.rect
        return (s + j * self.step, w + i * self.step)

    def water(self, i, j):
        return not self.mask[j * self.nx + i]

    def near_water(self, lat, lon, span=12):
        """The nearest navigable cell to a slip, which is itself on the shore."""
        i0, j0 = self.cell(lat, lon)
        if self.water(i0, j0):
            return (i0, j0)
        for r in range(1, span + 1):
            best = None
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    i, j = i0 + di, j0 + dj
                    if 0 <= i < self.nx and 0 <= j < self.ny and self.water(i, j):
                        d = di * di + dj * dj
                        if best is None or d < best[0]:
                            best = (d, (i, j))
            if best:
                return best[1]
        return (i0, j0)

    def route(self, a, b):
        """A water track from a to b as (lat, lon) points, or the straight line."""
        import heapq
        start, goal = self.near_water(*a), self.near_water(*b)

        def h(c):
            return math.hypot(c[0] - goal[0], c[1] - goal[1])

        openq = [(h(start), 0.0, start)]
        came, best = {}, {start: 0.0}
        seen = set()
        while openq:
            _, g, cur = heapq.heappop(openq)
            if cur in seen:
                continue
            seen.add(cur)
            if cur == goal:
                break
            i, j = cur
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if not (0 <= ni < self.nx and 0 <= nj < self.ny):
                        continue
                    # the slips themselves are on the shore, so the two ends are
                    # allowed to be land; nothing in between is
                    if not self.water(ni, nj):
                        continue
                    ng = g + math.hypot(di, dj)
                    if ng < best.get((ni, nj), 1e18):
                        best[(ni, nj)] = ng
                        came[(ni, nj)] = cur
                        heapq.heappush(openq, (ng + h((ni, nj)), ng, (ni, nj)))
        if goal not in came and goal != start:
            return [a, b]
        path, cur = [goal], goal
        while cur in came:
            cur = came[cur]
            path.append(cur)
        path.reverse()
        pts = [self.pos(*c) for c in path]
        # A coarse tolerance here straightens the track back across the island
        # it was routed around, so it stays fine.
        pts = rdp(pts, self.step * 0.25)
        return [a] + pts + [b]


def _signed_area(ring) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2


# ------------------------------------------------------------- simplification

def rdp(points, eps: float):
    """Ramer-Douglas-Peucker, iterative so a 40,000-point coast cannot blow
    the recursion limit."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        (x1, y1), (x2, y2) = points[i], points[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        worst, at = -1.0, None
        for k in range(i + 1, j):
            x, y = points[k]
            if norm == 0:
                d = math.hypot(x - x1, y - y1)
            else:
                d = abs(dy * (x - x1) - dx * (y - y1)) / norm
            if d > worst:
                worst, at = d, k
        if worst > eps and at is not None:
            keep[at] = True
            stack.append((i, at))
            stack.append((at, j))
    return [p for p, k in zip(points, keep) if k]


# ------------------------------------------------------------------ svg paths

def num(v: float) -> str:
    """One decimal, with the decimal dropped when it is zero.

    A coastline is tens of thousands of numbers; trimming ".0" and leaning on
    SVG's implicit lineto takes a fifth off the weight of the page.
    """
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def points_d(pts, close: bool = True) -> str:
    d = "M " + " ".join(f"{num(x)} {num(y)}" for x, y in pts)
    return d + (" Z" if close else "")


def path_d(rings, proj: Proj, eps: float = 0.3, close: bool = True) -> str:
    """Project, simplify and write rings as one SVG path."""
    out = []
    for ring in rings:
        pts = rdp([proj(lon, lat) for lon, lat in ring], eps)
        if len(pts) < (3 if close else 2):
            continue
        out.append(points_d(pts, close))
    return " ".join(out)


def clip_ring(ring, rect):
    """Sutherland-Hodgman: a polygon cut down to the rect it is drawn in."""
    w, s, e, n = rect
    edges = (
        (lambda p: p[0] >= w, lambda a, b: (w, a[1] + (b[1] - a[1]) * (w - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= e, lambda a, b: (e, a[1] + (b[1] - a[1]) * (e - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= s, lambda a, b: (a[0] + (b[0] - a[0]) * (s - a[1]) / (b[1] - a[1]), s)),
        (lambda p: p[1] <= n, lambda a, b: (a[0] + (b[0] - a[0]) * (n - a[1]) / (b[1] - a[1]), n)),
    )
    poly = list(ring)
    for inside, cut in edges:
        if not poly:
            return []
        out = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            ain, bin_ = inside(a), inside(b)
            if ain:
                out.append(a)
            if ain != bin_ and a != b:
                out.append(cut(a, b))
        poly = out
    return poly
