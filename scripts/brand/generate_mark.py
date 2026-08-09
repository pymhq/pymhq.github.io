#!/usr/bin/env python3
"""Generate the osmanthus brand mark and the icon set it feeds.

This is the source of truth for /assets/brand/*. The committed SVG is machine
generated — do not hand-edit it; change the parameters here and re-run.

  python3 scripts/brand/generate_mark.py            # SVGs only (no deps)
  python3 scripts/brand/generate_mark.py --png      # SVGs + PNGs
  python3 scripts/brand/generate_mark.py --check    # verify reproducibility

The drawing follows the real habit of Osmanthus fragrans: opposite lanceolate
leaves, florets clustered in the leaf axils (never at the branch tip), dew only
on the lowest leaf tips. Output is monochrome; one artwork serves every size,
scaled by the browser (no hand-tuned small rasters).

Deterministic: all randomness is seeded (SEED), so re-running produces a
byte-identical SVG. Verified with --check.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import sys

# ---------------------------------------------------------------- parameters

SEED = 7
INK = "#2f4436"          # ink green, the single brand colour
INK_DARK = "#cfe0d4"     # swapped in automatically under prefers-color-scheme: dark
VB = 200                 # drawing canvas (viewBox units)
MIN_W = 1.5              # floor on stroke width: thinner hairlines vanish when scaled down

CROWN = dict(cx=100, ground=176, crown_c=(100, 94), rx=66, ry=56)
DENSITY = dict(nleaf=112, flowers=18, dew_n=6, leaf_base=15.0, spacing=9.0)
RING = dict(r=91.0, w=7.0)          # the "V2" ring chosen for the icon
FIT = (126, 118)                    # artwork box inside the ring
ART_CENTRE = (100, 88)

# The tree used to fill (143, 134) centred at (100, 102), which left 18 of the
# 200 canvas units between the trunk base and the ring — not enough for water at
# any size. Fitting it smaller and higher opens a 36-unit band; the icon reads
# better at 32px for it, the crown being less crowded.

# 潺潺流水, flowing left. There is no arrowhead and no second colour available,
# so the direction is carried by the shapes: every ripple tapers to nothing at
# its left end, the ripples shorten and thin as they go, and the stone's wake
# opens downstream. Two variants, because one drawing cannot serve both ends of
# the size range:
#   icon    ripples inside the closed ring — the ring is what keeps the
#           silhouette readable at 16px, so it stays shut
#   display the ring opens at the bottom and the water closes it instead. Only
#           for 128px and up: at 32px the outline stops reading as a circle
#           while the water that justifies the break is barely there.
WATER_ICON = dict(
    # ripple rows as (offset below the waterline, span, amplitude, width); the
    # stone and the trailing dashes are offsets from the ground line, not from
    # the waterline, so `top` can move without dragging them along
    rows=((0.0, 0.95, 2.6, 3.4), (7.5, 0.88, 2.2, 2.8),
          (14.5, 0.74, 1.8, 2.4), (21.0, 0.52, 1.4, 2.0)),
    stone=(118.0, 11.0, 6.6, 3.4),
    dashes=((74, 5.0, 7.0), (68, 12.0, 5.0), (78, 19.0, 3.6)),
    top=3.0,
)
WATER_DISPLAY = dict(
    rows=((0.0, 0.99, 4.2), (8.0, 0.94, 3.0), (15.5, 0.82, 2.4), (22.0, 0.60, 1.9)),
    top=6.0,
    ring_gap=(28, 152),             # the stretch of ring the water takes over
)

# ink extents of the bare artwork, measured once in a browser with getBBox();
# used to fit the drawing inside the ring without eyeballing it
ART_BBOX = (15.12, 17.35, 170.11, 158.65)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "assets", "brand")

# Scale and offset the fit produces, and the height the trunk lands at once
# fitted — derived rather than typed in, so the water follows FIT if it moves.
_FIT_S = min(FIT[0] / ART_BBOX[2], FIT[1] / ART_BBOX[3])
_FIT_TY = ART_CENTRE[1] - _FIT_S * (ART_BBOX[1] + ART_BBOX[3] / 2)
GROUND_Y = _FIT_TY + _FIT_S * CROWN["ground"]
R_IN = RING["r"] - RING["w"] / 2


# ------------------------------------------------------------------- helpers


def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _sha(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def P(d: str, w: float, **kw) -> str:
    w = max(w, MIN_W)
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<path d="{d}" stroke-width="{f(w)}"{extra}/>'


# --------------------------------------------------------------------- parts


def leaf(x, y, ang, L, W):
    """Filled lanceolate leaf — solid so the crown reads as mass, not hatching."""
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    tx, ty = x + dx * L, y + dy * L
    d = [f"M{f(x)} {f(y)}"]
    for s in (1, -1):
        c1 = (x + dx * L * 0.22 + nx * s * W * 1.05, y + dy * L * 0.22 + ny * s * W * 1.05)
        c2 = (x + dx * L * 0.72 + nx * s * W * 0.92, y + dy * L * 0.72 + ny * s * W * 0.92)
        if s == 1:
            d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(tx)} {f(ty)}")
        else:
            d.append(f"C{f(c2[0])} {f(c2[1])} {f(c1[0])} {f(c1[1])} {f(x)} {f(y)}")
    return f'<path d="{" ".join(d)} Z" fill="currentColor" stroke="none"/>'


def floret(x, y, r, w=0.9):
    """One four-petalled osmanthus flower."""
    out = []
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        out.append(f'<circle cx="{f(x + math.cos(a) * r)}" cy="{f(y + math.sin(a) * r)}" '
                   f'r="{f(r * 0.62)}" stroke-width="{f(max(w, MIN_W))}"/>')
    out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.3)}" '
               f'fill="currentColor" stroke="none"/>')
    return "".join(out)


def flower_cluster(x, y, ang, rng, n=5, r=2.0, spread=4.8, w=0.9):
    """Axillary cluster — sits in a leaf axil, which is where osmanthus flowers.

    Note the two separate rng.uniform() calls for the x and y offsets: each axis
    gets its own angle, which is not what you would write from scratch. It is
    kept exactly as-is because the committed assets/brand/logo-mark.svg is the
    source of truth, and any change to the order or number of draws from the
    seeded RNG shifts every floret afterwards. Verify with --check after edits.
    """
    return "".join(
        floret(x + math.cos(ang + rng.uniform(-1.1, 1.1)) * spread * (0.25 + 0.75 * i / n),
               y + math.sin(ang + rng.uniform(-1.1, 1.1)) * spread * (0.25 + 0.75 * i / n),
               r * rng.uniform(0.85, 1.1), w)
        for i in range(n)
    )


def dew(x, y, r, w=1.5):
    """Dew bead clinging to a leaf tip, with a small specular arc."""
    return (
        f'<path d="M{f(x-r*0.66)} {f(y-r*0.6)} '
        f'C{f(x-r*1.02)} {f(y+r*0.3)} {f(x-r*0.52)} {f(y+r)} {f(x)} {f(y+r)} '
        f'C{f(x+r*0.52)} {f(y+r)} {f(x+r*1.02)} {f(y+r*0.3)} {f(x+r*0.66)} {f(y-r*0.6)} '
        f'Q{f(x)} {f(y-r*0.16)} {f(x-r*0.66)} {f(y-r*0.6)} Z" '
        f'stroke-width="{f(max(w, MIN_W))}"/>'
        + P(f"M{f(x-r*0.42)} {f(y+r*0.16)} a{f(r*0.55)} {f(r*0.55)} 0 0 1 "
            f"{f(r*0.3)} {f(-r*0.42)}", 0.9, opacity="0.7")
    )


# ---------------------------------------------------------------- the water


def chord(y: float, r: float = None) -> float:
    """Half-width available at height y, inside the ring by default."""
    r = R_IN if r is None else r
    return math.sqrt(max(r * r - (y - 100) ** 2, 0.0))


def wave(y, x_right, x_left, amp, cycles, phase=0.0, damp=1.0, n=72):
    """Ripple centreline, sampled right to left — the direction of travel.
    damp shrinks the undulation towards the left, as a ripple losing energy does.
    """
    pts = []
    for i in range(n):
        t = i / (n - 1)
        pts.append((x_right + (x_left - x_right) * t,
                    y + math.sin(phase + t * cycles * 2 * math.pi)
                    * amp * (1 - (1 - damp) * t)))
    return pts


def clip_inside(pts, margin=2.0):
    """Drop the stretch that would fall outside the ring. The interior narrows
    fast this low down, and a ripple built from a chord width is one sign error
    away from spilling out of the mark."""
    return [p for p in pts if math.hypot(p[0] - 100, p[1] - 100) < R_IN - margin]


def ribbon(pts, w_start, w_end):
    """Filled taper along a centreline. With w_end=0 the downstream tip comes to
    a real point, which a stroked path cannot do at any width."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, n - 1)]
        tx, ty = x1 - x0, y1 - y0
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        h = (w_start + (w_end - w_start) * (i / (n - 1))) / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    d = ("M" + " L".join(f"{f(x)} {f(y)}" for x, y in left)
         + " L" + " L".join(f"{f(x)} {f(y)}" for x, y in reversed(right)) + " Z")
    return f'<path d="{d}" fill="currentColor" stroke="none"/>'


def eddy(x, y, r, w=1.8, turns=0.62):
    """A curl at the downstream tip, hooking over the way an eddy does."""
    pts = []
    for i in range(26):
        t = i / 25
        a = math.pi * 0.15 + turns * 2 * math.pi * t
        rr = r * (1 - 0.72 * t)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    return P("M" + " L".join(f"{f(px)} {f(py)}" for px, py in pts), w)


def stone(x, y, rx, ry, w=1.8):
    """A stone breaking the surface. Its wake opens downstream — to the left —
    which is the most literal of the direction cues in the drawing."""
    out = [P(f"M{f(x - rx)} {f(y)} Q{f(x)} {f(y - ry * 2.1)} {f(x + rx)} {f(y)}", w)]
    for s in (-1, 1):
        out.append(P(f"M{f(x - rx * 0.75)} {f(y + s * 0.6)} q{f(-rx * 1.7)} "
                     f"{f(s * ry * 0.85)} {f(-rx * 3.0)} {f(s * ry * 1.15)}",
                     w * 0.62, opacity="0.85"))
    return "".join(out)


def water_icon() -> str:
    """Ripples in the band below the trunk, inside the closed ring."""
    cfg = WATER_ICON
    y_top = GROUND_Y + cfg["top"]
    out = []
    for dy, span, amp, w in cfg["rows"]:
        y = y_top + dy
        c = chord(y)
        line = clip_inside(wave(y, 100 + c * span, 100 - c * span, amp, 2.3,
                                phase=dy * 0.7, damp=0.45), w / 2 + 1)
        if len(line) > 3:
            out.append(ribbon(line, w, 0.0))
    sx, sdy, srx, sry = cfg["stone"]
    out.append(stone(sx, GROUND_Y + sdy, srx, sry))
    for x, dy, ln in cfg["dashes"]:
        out.append(P(f"M{f(x)} {f(GROUND_Y + dy)} q{f(-ln * 0.55)} -1.2 {f(-ln)} 0",
                     1.8, opacity="0.9"))
    return "".join(out)


def water_display() -> str:
    """Wider ripples that run out to the ring line and close the gap in it."""
    cfg = WATER_DISPLAY
    y_top = GROUND_Y + cfg["top"]
    out = []
    for dy, span, w in cfg["rows"]:
        y = y_top + dy
        c = chord(y, RING["r"])
        out.append(ribbon(wave(y, 100 + c * span, 100 - c * span,
                               2.4 - dy * 0.05, 2.1, phase=dy * 0.6, damp=0.4), w, 0.0))
    out.append(eddy(100 - chord(y_top, RING["r"]) * 0.99 + 6, y_top - 4.0, 5.0))
    return "".join(out)


def ring(gap=None) -> str:
    """The closed ring, or an arc of it where the water takes over."""
    if gap is None:
        return f'<circle cx="100" cy="100" r="{f(RING["r"])}" stroke-width="{f(RING["w"])}"/>'
    a0, a1 = gap
    p0 = (100 + math.cos(math.radians(a1)) * RING["r"],
          100 + math.sin(math.radians(a1)) * RING["r"])
    p1 = (100 + math.cos(math.radians(a0)) * RING["r"],
          100 + math.sin(math.radians(a0)) * RING["r"])
    return P(f"M{f(p0[0])} {f(p0[1])} A{f(RING['r'])} {f(RING['r'])} 0 1 1 "
             f"{f(p1[0])} {f(p1[1])}", RING["w"])


# ---------------------------------------------------------------- the drawing


def artwork() -> str:
    """Trunk + limbs + dense crown of solid leaves + axillary florets + dew."""
    rng = random.Random(SEED)
    cx, ground = CROWN["cx"], CROWN["ground"]
    crown_c, rx, ry = CROWN["crown_c"], CROWN["rx"], CROWN["ry"]
    nleaf, flowers = DENSITY["nleaf"], DENSITY["flowers"]
    dew_n, leaf_base, spacing = DENSITY["dew_n"], DENSITY["leaf_base"], DENSITY["spacing"]

    out = []
    fork = crown_c[1] + ry * 0.5
    # trunk, kept short so the mark's mass sits centre-high in the square
    out.append(P(f"M{f(cx-4)} {f(ground)} C{f(cx-2)} {f(ground-16)} {f(cx+2)} "
                 f"{f(ground-26)} {f(cx+1)} {f(fork)}", 5.0))
    out.append(P(f"M{f(cx-10)} {f(ground)} q6 -4 6 -10", 1.8, opacity="0.85"))   # root flare
    out.append(P(f"M{f(cx+9)} {f(ground)} q-5 -4 -5 -9", 1.8, opacity="0.85"))
    # primary limbs fanning into the crown, each with two pairs of twigs
    for a, ln, w in (
        (-1.57, 44, 3.4), (-1.05, 39, 3.0), (-2.10, 39, 3.0),
        (-0.66, 31, 2.5), (-2.50, 31, 2.5), (-1.30, 41, 2.6), (-1.85, 41, 2.6),
    ):
        bx, by = cx + 1, fork
        ex, ey = bx + math.cos(a) * ln, by + math.sin(a) * ln
        mx = bx + math.cos(a) * ln * 0.5 - math.sin(a) * ln * 0.12
        my = by + math.sin(a) * ln * 0.5 + math.cos(a) * ln * 0.12
        out.append(P(f"M{f(bx)} {f(by)} Q{f(mx)} {f(my)} {f(ex)} {f(ey)}", w))
        for k in (0.58, 0.84):
            sx, sy = bx + (ex - bx) * k, by + (ey - by) * k
            for s in (1, -1):
                a2 = a + s * 0.55
                out.append(P(f"M{f(sx)} {f(sy)} l{f(math.cos(a2)*12)} "
                             f"{f(math.sin(a2)*12)}", 1.6))
    # crown: rejection-sample leaf positions inside the ellipse, orient outward
    placed, tries = [], 0
    while len(placed) < nleaf and tries < nleaf * 40:
        tries += 1
        px = rng.uniform(crown_c[0] - rx, crown_c[0] + rx)
        py = rng.uniform(crown_c[1] - ry, crown_c[1] + ry)
        u = ((px - crown_c[0]) / rx) ** 2 + ((py - crown_c[1]) / ry) ** 2
        if u > 1.0:
            continue
        if placed and min(math.hypot(px - qx, py - qy) for qx, qy, _ in placed) < spacing:
            continue
        ang = math.atan2(py - crown_c[1], px - crown_c[0]) + rng.uniform(-0.5, 0.5)
        L = leaf_base + 7 * u + rng.uniform(-2, 2)
        placed.append((px, py, ang))
        out.append(leaf(px, py, ang, L, L * 0.235))
    for _ in range(flowers):
        px, py, ang = placed[rng.randrange(len(placed))]
        out.append(flower_cluster(px, py, ang, rng))
    # dew only on the lowest leaf tips
    low = sorted(placed, key=lambda p: -p[1])[: dew_n * 3]
    rng.shuffle(low)
    for (px, py, ang) in low[:dew_n]:
        out.append(dew(px + math.cos(ang) * leaf_base * 1.25,
                       py + math.sin(ang) * leaf_base * 1.25 + 2.4, 3.0))
    return "".join(out)


def fitted(art: str) -> str:
    """Scale the measured ink box of the artwork into FIT, centred at ART_CENTRE."""
    x, y, w, h = ART_BBOX
    s = min(FIT[0] / w, FIT[1] / h)
    tx = ART_CENTRE[0] - s * (x + w / 2)
    ty = ART_CENTRE[1] - s * (y + h / 2)
    return f'<g transform="translate({tx:.3f} {ty:.3f}) scale({s:.4f})">{art}</g>'


def build_svgs() -> dict[str, str]:
    """Two tiers, one drawing. The icon keeps its ring shut because that outline
    is what survives 16px; the display variant lets the water close the circle,
    which only works from about 128px up."""
    art = fitted(artwork())
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB} {VB}" '
            f'width="{VB}" height="{VB}" fill="none" stroke="currentColor" '
            f'stroke-linecap="round" stroke-linejoin="round">')
    style = (f"<style>svg{{color:{INK}}}"
             f"@media (prefers-color-scheme:dark){{svg{{color:{INK_DARK}}}}}</style>")

    def flatten(svg: str) -> str:
        return (svg.replace('stroke="currentColor"', f'stroke="{INK}"')
                   .replace('fill="currentColor"', f'fill="{INK}"'))

    out = {}
    for prefix, title, body in (
        ("logo-mark", "osmanthus mark", ring() + water_icon() + art),
        ("logo-mark-display", "osmanthus mark, display",
         ring(WATER_DISPLAY["ring_gap"]) + water_display() + art),
    ):
        opened = head + f"<title>Andy Peng — {title}</title>"
        out[f"{prefix}.svg"] = opened + style + body + "</svg>"
        out[f"{prefix}-flat.svg"] = flatten(opened + body + "</svg>")
    return out


# ------------------------------------------------------------------- rasters


def build_pngs(flat_svg: str, out_dir: str = OUT_DIR) -> list[str]:
    """Rasterise once at 1024 and downsample — keeps hairlines as greys.

    Drawing straight into a small canvas drops any stroke thinner than one
    device pixel; LANCZOS from a large master keeps it as partial alpha.
    """
    try:
        from PIL import Image
        from playwright.sync_api import sync_playwright
    except ImportError as exc:                      # pragma: no cover
        print(f"  PNG step skipped — missing dependency: {exc}")
        print("  pip install pillow playwright && playwright install chromium")
        return []

    os.makedirs(out_dir, exist_ok=True)
    master_path = os.path.join(out_dir, ".master-1024.png")
    big = flat_svg.replace(f'width="{VB}" height="{VB}"', 'width="1024" height="1024"')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1024, "height": 1024})
        pg.set_content(f'<body style="margin:0;width:1024px;height:1024px">{big}</body>')
        pg.wait_for_timeout(300)
        pg.screenshot(path=master_path, omit_background=True)
        b.close()

    master = Image.open(master_path).convert("RGBA")
    written = []
    for size, name in ((192, "icon-192.png"), (512, "icon-512.png")):
        master.resize((size, size), Image.LANCZOS).save(os.path.join(out_dir, name))
        written.append(name)
    # apple-touch-icon: transparent, inset so iOS's rounded mask never clips the ring
    at = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    at.alpha_composite(master.resize((168, 168), Image.LANCZOS), (6, 6))
    at.save(os.path.join(out_dir, "apple-touch-icon.png"))
    written.append("apple-touch-icon.png")
    os.remove(master_path)
    return written


# ---------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--png", action="store_true", help="also rasterise the PNG icons")
    ap.add_argument("--check", action="store_true",
                    help="compare generated SVGs against the files on disk, write nothing")
    args = ap.parse_args()

    svgs = build_svgs()
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.check:
        bad = 0
        for name, body in svgs.items():
            path = os.path.join(OUT_DIR, name)
            on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            same = on_disk == body
            print(f"  {'OK  ' if same else 'DIFF'} {name}  "
                  f"generated sha256={hashlib.sha256(body.encode()).hexdigest()[:12]}  "
                  f"on-disk sha256={hashlib.sha256(on_disk.encode()).hexdigest()[:12]}")
            bad += 0 if same else 1
        # rasters too, into a scratch dir so nothing on disk is touched
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for name in build_pngs(svgs["logo-mark-flat.svg"], tmp):
                gen = _sha(os.path.join(tmp, name))
                disk = _sha(os.path.join(OUT_DIR, name))
                same = gen == disk
                print(f"  {'OK  ' if same else 'DIFF'} {name}  "
                      f"generated sha256={gen[:12]}  on-disk sha256={disk[:12]}")
                bad += 0 if same else 1
        print("reproducible — regenerating gives exactly the committed files"
              if not bad else f"{bad} file(s) differ")
        return 1 if bad else 0

    for name, body in svgs.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"  wrote assets/brand/{name}  ({len(body):,} bytes)")
    if args.png:
        for name in build_pngs(svgs["logo-mark-flat.svg"]):
            size = os.path.getsize(os.path.join(OUT_DIR, name))
            print(f"  wrote assets/brand/{name}  ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
