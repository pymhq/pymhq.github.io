"""Report what collides on the to-scale Salish Sea sheet.

The sheet is generated, so its errors are systematic: if the label placer is
told a doodle is 22 units wide when the Hoh rain forest glyph is 63, every
label near that glyph lands on top of it, sixty times over. This reads the
generated markup back and measures everything on it, so a collision shows up as
a number instead of as a complaint about the picture.

What it measures, all in sheet units:
  * every text on the map, rotated ones included, as an oriented box
  * every doodle, at the size taken from its own path data
  * every cluster badge

Usage:
    python3 scripts/check_salish_sheet.py            # summary
    python3 scripts/check_salish_sheet.py --all      # every pair
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_salish_geo_panel import (  # noqa: E402
    FONT_W, VB_H, VB_W, glyph_extents, panel2_defs,
)

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps.html"

# Apron furniture is not on the map. Hover labels ARE measured: "invisible until
# you ask for it" was wrong, because when you do ask for it it lands on top of
# whatever printed text is already there, and that is what the reader sees.
IGNORED_TEXT = {"sg-badge-num", "rt-quest-item", "rt-quest-title"}
HOVER_TEXT = "rt-poi-label"


def sheets(html: str):
    """Every generated sheet: its id, its whole svg, and its drawing (no apron)."""
    i = html.index("BEGIN generated: salish sea")
    j = html.index("END generated: salish sea")
    out = []
    for m in re.finditer(r'<svg class="sg-sheet" id="sg-sheet-([a-z]+)".*?</svg>',
                         html[i:j], re.S):
        svg = m.group(0)
        body = svg[svg.index("</defs>"):svg.index('<g class="sg-apron-layer">')]
        box = re.search(r'data-map-only="([\d.]+) 0 ([\d.]+)', svg)
        span = (float(box.group(1)), float(box.group(1)) + float(box.group(2))) \
            if box else (0.0, VB_W)
        out.append((m.group(1), svg, body, span))
    return out


def poi_origins(body: str):
    """Where each rt-poi group sits, so its hover label can be placed globally."""
    spans = []
    for m in re.finditer(r'<g class="rt-poi" data-name="([^"]+)" '
                         r'transform="translate\((-?[\d.]+), (-?[\d.]+)\)">', body):
        spans.append((m.start(), m.group(1), float(m.group(2)), float(m.group(3))))
    return spans


def owner_of(pos, spans, body):
    """The rt-poi group a piece of markup at `pos` belongs to, if any."""
    best = None
    for start, name, x, y in spans:
        if start <= pos:
            best = (start, name, x, y)
        else:
            break
    if best is None:
        return None
    # only if the group has not closed before pos
    depth = 0
    for m in re.finditer(r"<g\b|</g>", body[best[0]:pos]):
        depth += 1 if m.group(0) == "<g" else -1
        if depth <= 0 and m.group(0) == "</g>":
            return None
    return best[1], best[2], best[3]


def text_boxes(body: str):
    spans = poi_origins(body)
    out = []
    for m in re.finditer(r'<text class="([^"]+)"[^>]*?x="(-?[\d.]+)" y="(-?[\d.]+)" '
                         r'text-anchor="(\w+)"([^>]*)>([^<]*)</text>', body):
        cls, x, y, anchor, rest, t = (m.group(1), float(m.group(2)), float(m.group(3)),
                                      m.group(4), m.group(5), m.group(6))
        if cls in IGNORED_TEXT or not t.strip():
            continue
        kind = "hover" if cls == HOVER_TEXT else "text"
        size = None
        sm = re.search(r"font-size:([\d.]+)px", rest)
        if sm:
            size = float(sm.group(1))
        if kind == "hover":
            own = owner_of(m.start(), spans, body)
            if own:
                x, y = x + own[1], y + own[2]
        w = FONT_W.get(cls, 5.6) * len(t) * ((size / 11.0) if size else 1.0)
        h = (size or (13.0 if "big" in cls else 11.0)) * 0.95
        x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
        cx, cy = x0 + w / 2, y - h / 2 + 2
        rot = 0.0
        rm = re.search(r"rotate\((-?[\d.]+)", rest)
        if rm:
            rot = float(rm.group(1))
            # rotation is about the anchor point, so the centre swings with it
            a = math.radians(rot)
            dx, dy = cx - x, cy - y
            cx, cy = x + dx * math.cos(a) - dy * math.sin(a), \
                y + dx * math.sin(a) + dy * math.cos(a)
        out.append(dict(kind=kind, label=t, cx=cx, cy=cy, w=w, h=h, rot=rot))
    return out


def glyph_boxes(body: str, sizes: dict):
    out = []
    for m in re.finditer(r'<use href="#sg-([a-z_-]+)"'
                         r'(?:[^>]*?transform="translate\((-?[\d.]+),\s*(-?[\d.]+)\)'
                         r'(?:\s*scale\((-?[\d.]+)[^)]*\))?")?[^>]*/>', body):
        name = m.group(1)
        if m.group(2) is None:
            continue
        x, y = float(m.group(2)), float(m.group(3))
        s = abs(float(m.group(4))) if m.group(4) else 1.0
        w, h = sizes.get(name, (24.0, 24.0))
        out.append(dict(kind="glyph", label=name, cx=x, cy=y,
                        w=max(w * s, 8), h=max(h * s, 8), rot=0.0))
    # a doodle inside a translated group: <g transform="translate(x, y) scale(s)">
    for m in re.finditer(r'<g transform="translate\((-?[\d.]+),\s*(-?[\d.]+)\)'
                         r'\s*scale\((-?[\d.]+)\)"><use href="#sg-([a-z_-]+)"/></g>', body):
        x, y, s, name = (float(m.group(1)), float(m.group(2)),
                         abs(float(m.group(3))), m.group(4))
        w, h = sizes.get(name, (24.0, 24.0))
        out.append(dict(kind="glyph", label=name, cx=x, cy=y,
                        w=max(w * s, 8), h=max(h * s, 8), rot=0.0))
    # a place: <g class="rt-poi" ... translate(x, y)> with its glyph inside
    for m in re.finditer(r'<g class="rt-poi" data-name="([^"]+)" '
                         r'transform="translate\((-?[\d.]+), (-?[\d.]+)\)">'
                         r'(?:<use href="#sg-([a-z_-]+)"(?: transform="scale\((-?[\d.]+)))?',
                         body):
        name, x, y = m.group(1), float(m.group(2)), float(m.group(3))
        ic, s = m.group(4), abs(float(m.group(5))) if m.group(5) else 1.0
        # A place drawn as a plain dot is 2.2 units of ink, not the 9 units the
        # fitter reserves for it. Measuring the reservation counted a name beside
        # a dot as a collision twenty-one times on the index sheet.
        if ic:
            w, h = sizes.get(ic, (9.0, 9.0))
        else:
            tail = body[m.end():m.end() + 200]
            w = h = 5.0 if 'class="sg-dot"' in tail else 9.0
        out.append(dict(kind="place", label=name, cx=x, cy=y,
                        w=max(w * s, 8), h=max(h * s, 8), rot=0.0))
    return out


def badge_boxes(svg: str):
    out = []
    for m in re.finditer(r'<circle class="sg-badge" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"',
                         svg):
        x, y, r = float(m.group(1)), float(m.group(2)), float(m.group(3))
        out.append(dict(kind="badge", label="+n", cx=x, cy=y, w=2 * r, h=2 * r, rot=0.0))
    return out


def corners(b):
    a = math.radians(b["rot"])
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = b["w"] / 2, b["h"] / 2
    return [(b["cx"] + dx * ca - dy * sa, b["cy"] + dx * sa + dy * ca)
            for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]


def overlap_area(b1, b2) -> float:
    """Separating-axis test on two oriented boxes, then an approximate area."""
    p1, p2 = corners(b1), corners(b2)
    for poly in (p1, p2):
        for i in range(4):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % 4]
            ax, ay = -(y2 - y1), x2 - x1
            r1 = [ax * x + ay * y for x, y in p1]
            r2 = [ax * x + ay * y for x, y in p2]
            if max(r1) <= min(r2) or max(r2) <= min(r1):
                return 0.0
    # both are small: the axis-aligned intersection of their bounds is close
    xs1 = [p[0] for p in p1]; ys1 = [p[1] for p in p1]
    xs2 = [p[0] for p in p2]; ys2 = [p[1] for p in p2]
    w = min(max(xs1), max(xs2)) - max(min(xs1), min(xs2))
    h = min(max(ys1), max(ys2)) - max(min(ys1), min(ys2))
    return max(w, 0) * max(h, 0)


def main() -> int:
    html = MAPS.read_text()
    sizes = glyph_extents(panel2_defs(html))
    total = 0
    for key, svg, body, span in sheets(html):
        items = text_boxes(body) + glyph_boxes(body, sizes) + badge_boxes(svg)
        texts = [b for b in items if b["kind"] == "text"]
        print(f"\n=== sheet {key}  ({len(svg) // 1024} KB) "
              f"map {span[0]:.0f}..{span[1]:.0f}")
        print(f"    {len(texts)} names, "
              f"{len([b for b in items if b['kind'] == 'glyph'])} doodles, "
              f"{len([b for b in items if b['kind'] == 'place'])} places")
        off = [b for b in texts
               if min(p[0] for p in corners(b)) < span[0] + 2
               or max(p[0] for p in corners(b)) > span[1] - 2]
        if off:
            print(f"    names touching the apron: {len(off)}  "
                  f"{[b['label'] for b in off]}")
        # Doodle on doodle is measured too: the three ducks were sitting on the
        # camp tent and the hen on the pottery, and skipping these pairs is why
        # nobody noticed.
        # Buckets, because they are not equally wrong. Two hover labels
        # overlapping is not a defect: only one is ever on screen. A hover label
        # over printed type is. So is one drawing on another. And two 2-unit dots
        # touching on an index sheet is the honest picture, not a fault.
        def dot(b):
            return b["kind"] == "place" and b["w"] <= 9.1 and b["h"] <= 9.1

        buckets = {"printed x printed": [], "hover x printed": [],
                   "type x drawing": [], "drawing x drawing": [],
                   "hover x hover (not a defect)": [], "dot x dot (not a defect)": []}
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                area = overlap_area(a, b)
                if area <= 6:
                    continue
                ka, kb, words = a["kind"], b["kind"], {"text", "hover"}
                if ka == "hover" and kb == "hover":
                    k = "hover x hover (not a defect)"
                elif dot(a) and dot(b):
                    k = "dot x dot (not a defect)"
                elif ka in words and kb in words:
                    k = "hover x printed" if "hover" in (ka, kb) else "printed x printed"
                elif ka in words or kb in words:
                    k = "type x drawing"
                else:
                    k = "drawing x drawing"
                buckets[k].append((area, a, b))
        soft = ("hover x hover (not a defect)", "dot x dot (not a defect)")
        real = sum(len(v) for k, v in buckets.items() if k not in soft)
        total += real
        print(f"    {len(texts)} names, {len([b for b in items if b['kind']=='hover'])}"
              f" hover, {len([b for b in items if b['kind']=='glyph'])} doodles, "
              f"{len([b for b in items if b['kind']=='place'])} places")
        print(f"    REAL DEFECTS: {real}")
        for k in list(buckets):
            v = sorted(buckets[k], reverse=True, key=lambda t: t[0])
            if not v:
                continue
            print(f"      {k:30} {len(v):4}")
            if k in soft:
                continue
            for area, a, b in (v if "--all" in sys.argv else v[:6]):
                print(f"        {area:6.0f}u²  {a['kind']:5s} {a['label'][:28]!r:32s} "
                      f"x {b['kind']:5s} {b['label'][:28]!r}")
    print(f"\ntotal collisions across sheets: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
