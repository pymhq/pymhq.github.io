#!/usr/bin/env python3
"""Water studies for the osmanthus mark — 潺潺流水, flowing left.

Nothing here touches the shipped mark. generate_mark.py is imported read-only
for the ring and the tree, six water layers are drawn on top, and the result
goes into a self-contained preview sheet next to this file:

    python3 scripts/brand/water/water_concepts.py
    open http://127.0.0.1:8123/scripts/brand/water/water-concepts.html

How a static, monochrome drawing says "leftward"
------------------------------------------------
There is no arrowhead available and no colour, so direction has to come out of
the shapes themselves. Four cues are used, and every concept combines at least
two so the reading does not depend on one trick:

  taper      a stroke that thins to nothing at its left end reads as water
             thinning out downstream; the thick end is where it came from
  wake       a stone parts the flow and the V opens *downstream*, i.e. to the
             left — the single most literal cue here
  curl       an eddy at the left tip, hooking over in the direction of travel
  grading    ripples that get shorter and sparser to the left, the way a
             shallow brook frays out

Two ways of drawing the ripples are deliberately mixed across the concepts, to
see which survives the icon sizes:

  stroked    uniform width with the MIN_W floor from generate_mark, so it
             cannot vanish when scaled down, but it cannot taper either
  ribbon     a filled shape whose half-width falls to zero, so it tapers
             properly — at the cost of the tip disappearing below ~32px

Read the 32px and 16px columns of the sheet before falling for the 256px one.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_mark as gm  # noqa: E402  (read-only: only its drawing functions)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "water-concepts.html")

VB = gm.VB
R_RING = gm.RING["r"]
R_IN = R_RING - gm.RING["w"] / 2          # inner edge of the ring stroke

# Where the trunk meets the ground once the artwork is fitted into the ring.
# Derived, not eyeballed, so it follows generate_mark if FIT ever changes.
_S = min(gm.FIT[0] / gm.ART_BBOX[2], gm.FIT[1] / gm.ART_BBOX[3])
_TY = gm.ART_CENTRE[1] - _S * (gm.ART_BBOX[1] + gm.ART_BBOX[3] / 2)
GROUND = _TY + _S * gm.CROWN["ground"]     # ≈169 in the 200-unit canvas
TRUNK_X = (100 - 7 * _S, 100 + 7 * _S)     # the width the trunk occludes

f = gm.f


# ----------------------------------------------------------------- geometry


def chord(y: float, r: float = R_IN) -> float:
    """Half-width available inside the ring at height y."""
    dy = y - 100
    return math.sqrt(max(r * r - dy * dy, 0.0))


def inside(pts, margin=2.0):
    """Keep only the stretch that stays inside the ring. Every water layer runs
    through this: the interior narrows fast near the bottom, and a ripple built
    from a chord width is one sign error away from spilling outside the mark."""
    return [p for p in pts if math.hypot(p[0] - 100, p[1] - 100) < R_IN - margin]


def wave(y, x_right, x_left, amp, cycles, phase=0.0, damp=1.0, n=72):
    """Ripple centreline, sampled right to left — the direction of travel.

    damp < 1 shrinks the undulation towards the left end, which is what a
    ripple running out of energy does.
    """
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = x_right + (x_left - x_right) * t
        a = amp * (1 - (1 - damp) * t)
        pts.append((x, y + math.sin(phase + t * cycles * 2 * math.pi) * a))
    return pts


def arc_pts(a_from, a_to, r, n=72, cx=100, cy=100):
    """Points along a circle, in degrees; increasing angle runs leftwards at
    the bottom of the mark, which is the direction the water travels."""
    return [
        (cx + math.cos(math.radians(a_from + (a_to - a_from) * i / (n - 1))) * r,
         cy + math.sin(math.radians(a_from + (a_to - a_from) * i / (n - 1))) * r)
        for i in range(n)
    ]


def split_at_trunk(pts, pad=2.0):
    """Break a centreline where the trunk stands, so the stream reads as
    passing behind it. A gap does the occluding; a paper-coloured halo would
    not survive the dark-mode variant of the icon."""
    lo, hi = TRUNK_X[0] - pad, TRUNK_X[1] + pad
    runs, cur = [], []
    for p in pts:
        if lo <= p[0] <= hi:
            if len(cur) > 2:
                runs.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 2:
        runs.append(cur)
    return runs


# -------------------------------------------------------------------- marks


def polyline(pts, w, **kw):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    return gm.P(d, w, **kw)


def ribbon(pts, w_start, w_end, **kw):
    """Filled taper along a centreline: full width at the first point, w_end at
    the last. With w_end=0 the left tip comes to a real point, which no stroked
    path can do."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1)
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, n - 1)]
        tx, ty = x1 - x0, y1 - y0
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        h = (w_start + (w_end - w_start) * t) / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    d = ("M" + " L".join(f"{f(x)} {f(y)}" for x, y in left)
         + " L" + " L".join(f"{f(x)} {f(y)}" for x, y in reversed(right)) + " Z")
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<path d="{d}" fill="currentColor" stroke="none"{extra}/>'


def curl(x, y, r, w=1.6, turns=0.62, cw=True):
    """Eddy at the downstream tip: a short spiral hooking over."""
    pts = []
    steps = 26
    for i in range(steps):
        t = i / (steps - 1)
        a = math.pi * 0.15 + turns * 2 * math.pi * t * (1 if cw else -1)
        rr = r * (1 - 0.72 * t)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    return polyline(pts, w)


def stone(x, y, rx, ry, w=1.8):
    """A stone breaking the surface, with the wake opening downstream (left)."""
    out = [gm.P(f"M{f(x - rx)} {f(y)} Q{f(x)} {f(y - ry * 2.1)} {f(x + rx)} {f(y)}", w)]
    for s in (-1, 1):
        out.append(gm.P(f"M{f(x - rx * 0.75)} {f(y + s * 0.6)} "
                        f"q{f(-rx * 1.7)} {f(s * ry * 0.85)} {f(-rx * 3.0)} "
                        f"{f(s * ry * 1.15)}", w * 0.62, opacity="0.85"))
    return "".join(out)


# ------------------------------------------------------------------ the base


def ring(dash_gap=None) -> str:
    """The shipped ring, or an arc of it when the water takes over a stretch."""
    if dash_gap is None:
        return f'<circle cx="100" cy="100" r="{f(R_RING)}" stroke-width="{f(gm.RING["w"])}"/>'
    a0, a1 = dash_gap                     # the stretch to leave to the water
    p0 = (100 + math.cos(math.radians(a1)) * R_RING, 100 + math.sin(math.radians(a1)) * R_RING)
    p1 = (100 + math.cos(math.radians(a0)) * R_RING, 100 + math.sin(math.radians(a0)) * R_RING)
    return gm.P(f"M{f(p0[0])} {f(p0[1])} A{f(R_RING)} {f(R_RING)} 0 1 1 {f(p1[0])} {f(p1[1])}",
                gm.RING["w"])


TREE = gm.fitted(gm.artwork())             # generated once; identical to the shipped mark
TREE_REF = '<use href="#tree"/>'           # 42 inline copies of it would be a 2MB page


def refit(fit, centre):
    """Re-fit the same artwork into a smaller box, higher up. Used by the two
    concepts that give the water real room instead of squeezing it into the
    18 units the shipped composition leaves below the trunk."""
    x, y, w, h = gm.ART_BBOX
    s = min(fit[0] / w, fit[1] / h)
    tx = centre[0] - s * (x + w / 2)
    ty = centre[1] - s * (y + h / 2)
    return (f'<g transform="translate({tx:.3f} {ty:.3f}) scale({s:.4f})">{gm.artwork()}</g>',
            ty + s * gm.CROWN["ground"], (100 - 7 * s, 100 + 7 * s))


TREE_UP, GROUND_UP, TRUNK_X_UP = refit((126, 118), (100, 88))
TREE_UP_REF = '<use href="#tree-up"/>'


def inline_trees(body: str) -> str:
    """Swap the <use> references for the artwork itself, for a standalone SVG
    (the raster comparison renders each mark on its own, with no shared defs)."""
    return body.replace(TREE_UP_REF, TREE_UP).replace(TREE_REF, TREE)


def mark(water: str = "", dash_gap=None, tree=None) -> str:
    """Water first so the tree's ink sits on top of it wherever they meet."""
    return ring(dash_gap) + water + (tree or TREE_REF)


# ------------------------------------------------------------------ concepts


def wa_brook():
    """Stroked ripples in the strip below the trunk. Uniform width, so nothing
    can drop out at 16px; direction comes from length grading and the wake."""
    out = []
    for y, span, amp, w in ((172.5, 0.92, 2.1, 2.6), (178.5, 0.80, 1.7, 2.2),
                            (183.5, 0.60, 1.3, 1.9)):
        c = chord(y)
        pts = inside(wave(y, 100 + c * span, 100 - c * span, amp, 2.4, damp=0.45), w / 2 + 1)
        if len(pts) > 3:
            out.append(polyline(pts, w))
    out.append(stone(94.0, 178.0, 6.0, 3.2))
    # a few frayed dashes trailing off to the left, shortening as they go
    for x, y, ln in ((74, 174.0, 6.5), (68, 179.5, 4.6), (78, 183.0, 3.4)):
        out.append(gm.P(f"M{f(x)} {f(y)} q{f(-ln * 0.55)} -1.2 {f(-ln)} 0", 1.8, opacity="0.9"))
    return mark("".join(out))


def wb_ring_current():
    """The ring itself becomes the stream along its lower-left run, so no new
    mass lands inside the mark. Flow enters at the bottom and tapers out top
    left; the silhouette changes, which is the price."""
    water = []
    for r, w in ((R_RING, 6.4), (R_RING - 10.5, 3.0), (R_RING - 18.0, 2.0)):
        water.append(ribbon(arc_pts(102, 212, r), w, 0.0))
    tip = arc_pts(212, 212, R_RING - 10.5, n=2)[0]
    water.append(curl(tip[0] - 1.5, tip[1] - 1.5, 4.6, 1.7))
    return mark("".join(water), dash_gap=(100, 214))


def wc_crossing():
    """A stream crossing the full interior and passing behind the trunk, with
    tapered tips. The most literal 潺潺流水, and the most ink."""
    out = []
    for y, amp, w, ph in ((170.0, 2.4, 3.4, 0.0), (177.0, 2.0, 2.8, 1.1),
                          (183.0, 1.4, 2.2, 2.2)):
        c = chord(y)
        line = inside(wave(y, 100 + c * 0.95, 100 - c * 0.98, amp, 2.2, phase=ph, damp=0.5),
                      w / 2 + 1)
        for run in split_at_trunk(line):
            # only the run that reaches the left edge gets the vanishing tip
            ends_left = run[-1][0] < 96
            out.append(ribbon(run, w, 0.0 if ends_left else w * 0.75))
    out.append(stone(112, 175.0, 6.5, 3.4))
    return mark("".join(out))


def wd_bank():
    """A bank running downhill to the left: the waterline is a long diagonal,
    which states the direction before any ripple is read."""
    out = []
    x_r, x_l = 100 + chord(163) * 0.98, 100 - chord(186) * 0.9
    for k, (dy, w) in enumerate(((0.0, 3.2), (6.0, 2.2), (11.5, 1.8))):
        pts = [(x_r + (x_l - x_r) * (i / 63),
                163 + dy + (186 - 163) * (i / 63) ** 1.35
                + math.sin(i / 63 * 2.1 * 2 * math.pi + k) * (2.0 - 0.5 * k))
               for i in range(64)]
        pts = [p for p in pts if math.hypot(p[0] - 100, p[1] - 100) < R_IN - 1]
        for run in split_at_trunk(pts):
            out.append(ribbon(run, w, 0.0 if run[-1][0] < 100 else w * 0.8))
    out.append(stone(126, 168.0, 5.6, 3.0))
    return mark("".join(out))

def we_ripples():
    """Concentric ripples opening to the left, the way a spreading ring gets
    carried downstream. Quietest of the six, and the least literal."""
    out = []
    cx, cy = 118.0, 177.0
    for i, (r, w) in enumerate(((9.0, 2.6), (15.0, 2.1), (21.5, 1.8), (28.0, 1.5))):
        a0, a1 = 118 + i * 6, 242 - i * 6          # an arc facing left
        pts = [p for p in arc_pts(a0, a1, r, n=48, cx=cx, cy=cy)
               if math.hypot(p[0] - 100, p[1] - 100) < R_IN - 1.5]
        if len(pts) > 3:
            out.append(ribbon(pts, w * 0.35, w) if False else polyline(pts, w))
    out.append(gm.P(f"M{f(cx)} {f(cy)} q-7 -1.4 -13 0", 1.8, opacity="0.9"))
    return mark("".join(out))


def wf_surface():
    """The mark standing in water: one waterline, a broken second line, and a
    hint of the trunk's reflection. Reads at every size because the waterline
    is a single long stroke."""
    out = []
    y = 174.0
    c = chord(y)
    out.append(ribbon(wave(y, 100 + c * 0.97, 100 - c * 0.99, 1.4, 1.6, damp=0.3), 3.0, 0.0))
    for x0, ln in ((116, 13.0), (100, 9.0), (86, 6.0)):
        out.append(gm.P(f"M{f(x0)} {f(y + 6.2)} q{f(-ln * 0.5)} -1.5 {f(-ln)} 0", 2.0,
                        opacity="0.9"))
    # reflection: the trunk again, shorter and broken, below the line
    out.append(gm.P(f"M{f(100.5)} {f(y + 2.5)} q-1.2 4 -0.4 7.5", 2.4, opacity="0.75"))
    out.append(curl(100 - c * 0.99 + 4.5, y - 2.0, 4.0, 1.6))
    return mark("".join(out))


def _brook_band(y_top, rows, stone_at, dashes, trunk=None):
    """Shared water band: graded ripples + a stone whose wake opens left."""
    out = []
    for dy, span, amp, w, taper in rows:
        y = y_top + dy
        c = chord(y)
        line = inside(wave(y, 100 + c * span, 100 - c * span, amp, 2.3, phase=dy * 0.7,
                           damp=0.45), w / 2 + 1)
        runs = split_at_trunk(line, 2.0) if trunk else [line]
        for run in runs:
            if len(run) < 4:
                continue
            out.append(ribbon(run, w, 0.0) if taper else polyline(run, w))
    out.append(stone(*stone_at))
    for x, y, ln in dashes:
        out.append(gm.P(f"M{f(x)} {f(y)} q{f(-ln * 0.55)} -1.2 {f(-ln)} 0", 1.8, opacity="0.9"))
    return "".join(out)


def wg_lifted():
    """Same tree, fitted smaller and higher, which opens a 36-unit band for the
    water instead of the 18 the shipped composition leaves. This is the only way
    the stream still reads at 48px — the water needs room, not finer drawing."""
    water = _brook_band(
        GROUND_UP + 3,
        ((0.0, 0.95, 2.6, 3.4, True), (7.5, 0.88, 2.2, 2.8, True),
         (14.5, 0.74, 1.8, 2.4, True), (21.0, 0.52, 1.4, 2.0, True)),
        (118.0, GROUND_UP + 11.0, 6.6, 3.4),
        ((74, GROUND_UP + 5.0, 7.0), (68, GROUND_UP + 12.0, 5.0), (78, GROUND_UP + 19.0, 3.6)),
    )
    return mark(water, tree=TREE_UP_REF)


def wh_water_base():
    """The stream closes the circle: the ring stops where the water starts, so
    the mark sits in the current rather than standing above a decoration. The
    strongest silhouette change of the eight, and the boldest."""
    water = []
    for dy, span, w in ((0.0, 0.99, 4.2), (8.0, 0.94, 3.0), (15.5, 0.82, 2.4),
                        (22.0, 0.60, 1.9)):
        y = GROUND_UP + 6 + dy
        c = chord(y, R_RING)                      # out to the ring line, not inside it
        line = wave(y, 100 + c * span, 100 - c * span, 2.4 - dy * 0.05, 2.1,
                    phase=dy * 0.6, damp=0.4)
        water.append(ribbon(line, w, 0.0))
    water.append(curl(100 - chord(GROUND_UP + 6, R_RING) * 0.99 + 6, GROUND_UP + 2.0, 5.0, 1.8))
    return mark("".join(water), dash_gap=(28, 152), tree=TREE_UP_REF)


CONCEPTS = [
    ("W0", "现状 · 无水", "现在线上的图标，作为对照。", mark(), False),
    ("WG", "抬树让水 Lifted, with a real brook",
     "把同一棵树缩到 88%、上移，底部让出 36 单位的水带（现状只有 18）。四道收尖水纹 + 分水石，"
     "48px 还读得出是水 —— 前面几版在小尺寸消失，不是画得不够细，而是没有地方。", wg_lifted(), True),
    ("WA", "溪脚 Brook at the foot",
     "不动树，只在树脚现有的窄缝里塞三道等宽描边水纹，越往左越短、越稀，配一块分水石（尾迹向左开口）。"
     "描边受 MIN_W 保护不会整条消失，但 96px 以下基本只剩一团灰。改动最小的一版。", wa_brook(), False),
    ("WB", "水环 Ring as current",
     "把圆环左下那段交给水：三道同心水纹沿环流动，右下入、左上收成尖，尖端一个小涡。"
     "内部不加任何笔墨，代价是改了图标的外轮廓（圆环出现缺口）。", wb_ring_current(), False),
    ("WH", "水托 Water as the base",
     "水直接替掉圆环底部：环在水面处断开，图标是立在流水里，而不是站在一处装饰上方。"
     "八版里外轮廓改动最大、也最有气势的一版。", wh_water_base(), False),
    ("WC", "过溪 Stream crossing",
     "水横穿整个内圆，在树干处断开表示从干后穿过，左端收成真正的尖。最像“潺潺流水”，"
     "也是墨量最大的一版，小尺寸下容易和树脚糊在一起。", wc_crossing(), False),
    ("WD", "岸线 Bank downhill",
     "水面本身是一条向左下倾斜的斜线 —— 在看清任何水纹之前，斜度已经说明了流向。"
     "但现状留给它的三角区太窄，只剩一小撮线。", wd_bank(), False),
    ("WE", "涟漪 Ripples drifting",
     "四道向左张开的同心弧，像被水带着走的涟漪。最安静，但“流向”是靠联想，不如尾迹直接。", we_ripples(), False),
    ("WF", "水面 Waterline & reflection",
     "整枚图标立在水里：一条长水线 + 一排断续短纹 + 树干的倒影残影。"
     "长水线在任何尺寸都读得出来，倒影是唯一能说明“站在水里”的元素。", wf_surface(), False),
]

SIZES = (256, 96, 48, 32, 16)


def svg(body, px):
    return (f'<svg width="{px}" height="{px}" viewBox="0 0 {VB} {VB}" fill="none" '
            f'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">'
            f"{body}</svg>")


cells = []
for key, name, note, body, pick in CONCEPTS:
    row = "".join(f'<div class="s"><span>{px}</span>{svg(body, px)}</div>' for px in SIZES)
    dark = f'<div class="s inv"><span>dark</span>{svg(body, 96)}</div>'
    cells.append(
        f'<div class="cell{" pick" if pick else ""}">'
        f'<div class="hd"><h3>{key} · {name}</h3>'
        f'{"<b>建议</b>" if pick else ""}</div>'
        f'<div class="row">{row}{dark}</div><p>{note}</p></div>'
    )

html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Water studies — 潺潺流水，向左流</title>
<style>
  body {{ margin:0; padding:34px; background:#fffdf8;
         font:13px/1.65 -apple-system,"Helvetica Neue",Arial,sans-serif; color:#16181d; }}
  h1 {{ font-size:19px; margin:0 0 6px; }}
  .lede {{ color:#5a616b; margin:0 0 24px; max-width:900px; }}
  .lede b {{ color:#16181d; }}
  .grid {{ display:grid; grid-template-columns:1fr; gap:20px; max-width:1180px; }}
  .cell {{ border:1px solid #eae4d8; border-radius:16px; padding:18px 22px; background:#fff; }}
  .cell.pick {{ border-color:#2f4436; box-shadow:0 0 0 3px rgba(47,68,54,.08); }}
  .hd {{ display:flex; align-items:baseline; gap:10px; margin-bottom:12px; }}
  h3 {{ margin:0; font-size:15px; }}
  .hd b {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase;
           color:#2f4436; border:1px solid #2f4436; border-radius:99px; padding:1px 8px; }}
  .row {{ display:flex; align-items:flex-end; gap:22px; flex-wrap:wrap; margin-bottom:10px; }}
  .s {{ text-align:center; line-height:0; }}
  .s span {{ display:block; line-height:1.4; font-size:10px; color:#9aa0a8; margin-bottom:4px; }}
  svg {{ color:#2f4436; }}
  .inv {{ background:#14201a; border-radius:12px; padding:8px 8px 4px; }}
  .inv span {{ color:#6f7d73; }}
  .inv svg {{ color:#cfe0d4; }}
  p {{ margin:0; font-size:12.5px; color:#5a616b; max-width:900px; }}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<g id="tree" fill="none" stroke="currentColor" stroke-linecap="round"
   stroke-linejoin="round">{TREE}</g>
<g id="tree-up" fill="none" stroke="currentColor" stroke-linecap="round"
   stroke-linejoin="round">{TREE_UP}</g></defs></svg>
<h1>桂花图标 + 潺潺流水（向左流）· 八个方案</h1>
<p class="lede">静态、单色、没有箭头，流向只能靠形状本身说明。这里用了四种线索，每个方案至少叠两种：
<b>收尖</b>（笔画向左收成无穷细，细的那头是去处）、<b>尾迹</b>（石头分水，V 字向下游即向左张开）、
<b>回涡</b>（左端一个顺流向的小卷）、<b>疏密</b>（越往左越短越稀，像浅溪散开）。<br>
水纹画法故意混用两种：<b>描边</b>受 generate_mark 的 MIN_W 保护，小尺寸不会消失但没法收尖；
<b>填充</b>能画出真正的尖，代价是尖端在 32px 以下先没。<b>请先看 32 / 16 两列再看 256 那列。</b><br>
一条画出来才发现的结论：现状的构图在树脚只留了 18 单位高的缝，任何水纹放进去到 96px 就成一团灰。
所以 WG / WH 两版把同一棵树缩小上移，先腾出 36 单位的水带 —— 差别不在画得细不细，在有没有地方。<br>
现有代码和 <code>assets/brand/</code> 一个字节都没动 —— 树和圆环是从 generate_mark.py 只读导入的。</p>
<div class="grid">{"".join(cells)}</div>
</body></html>
"""

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"wrote {os.path.relpath(OUT, gm.ROOT)} — {len(html):,} bytes, "
      f"{len(CONCEPTS) - 1} water concepts + baseline")


# Importing this module to reuse the concept functions rewrites the sheet, which
# is harmless and matches how ../drafts/*.py behave. See compare_wg_wh.py.
