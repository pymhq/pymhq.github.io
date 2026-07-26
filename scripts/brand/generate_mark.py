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
FIT = (143, 134)                    # artwork box inside the ring
ART_CENTRE = (100, 102)

# ink extents of the bare artwork, measured once in a browser with getBBox();
# used to fit the drawing inside the ring without eyeballing it
ART_BBOX = (15.12, 17.35, 170.11, 158.65)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "assets", "brand")


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
    art = artwork()
    inner = (f'<circle cx="100" cy="100" r="{f(RING["r"])}" '
             f'stroke-width="{f(RING["w"])}"/>' + fitted(art))
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB} {VB}" '
            f'width="{VB}" height="{VB}" fill="none" stroke="currentColor" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f"<title>Andy Peng — osmanthus mark</title>")
    themed = (head + f"<style>svg{{color:{INK}}}"
              f"@media (prefers-color-scheme:dark){{svg{{color:{INK_DARK}}}}}</style>"
              + inner + "</svg>")
    flat = (head + inner + "</svg>").replace(
        'stroke="currentColor"', f'stroke="{INK}"').replace(
        'fill="currentColor"', f'fill="{INK}"')
    return {"logo-mark.svg": themed, "logo-mark-flat.svg": flat}


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
