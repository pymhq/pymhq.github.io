#!/usr/bin/env python3
"""Round 5: Osmanthus fragrans (桂花), drawn naturalistically, with dew.

Botany the shapes follow:
  - evergreen, dense rounded crown
  - leaves strictly OPPOSITE (对生), leathery, lanceolate, serrate on the
    upper half, prominent midrib
  - flowers tiny and four-petalled, packed into clusters in the leaf axils
    (叶腋聚伞花序) — never at the branch tip
  - dew collects at the leaf tips, so beads hang from the lowest leaves only
"""
import math
import os
import random

VB = 200


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def P(d, w, **kw):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f'<path d="{d}" stroke-width="{f(w)}"{extra}/>'


# ------------------------------------------------------------------ leaf


def leaf_outline(x, y, ang, L, W, serrate=True, midrib=True, w=1.25):
    """Lanceolate osmanthus leaf: outline + midrib + fine serration."""
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    tx, ty = x + dx * L, y + dy * L
    out = []
    for s in (1, -1):
        c1 = (x + dx * L * 0.22 + nx * s * W * 1.05, y + dy * L * 0.22 + ny * s * W * 1.05)
        c2 = (x + dx * L * 0.72 + nx * s * W * 0.92, y + dy * L * 0.72 + ny * s * W * 0.92)
        out.append(
            P(f"M{f(x)} {f(y)} C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(tx)} {f(ty)}", w)
        )
    if midrib:
        out.append(P(f"M{f(x)} {f(y)} L{f(tx)} {f(ty)}", w * 0.62, opacity="0.85"))
    if serrate:
        for k in (0.5, 0.63, 0.76, 0.88):
            for s in (1, -1):
                px = x + dx * L * k + nx * s * W * (1 - abs(k - 0.55)) * 0.98
                py = y + dy * L * k + ny * s * W * (1 - abs(k - 0.55)) * 0.98
                out.append(
                    P(f"M{f(px)} {f(py)} l{f(dx*1.9 + nx*s*1.0)} {f(dy*1.9 + ny*s*1.0)}",
                      w * 0.5, opacity="0.8")
                )
    return "".join(out)


def leaf_solid(x, y, ang, L, W):
    """Filled leaf — used for canopy mass, with a notch of white for the midrib."""
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


# --------------------------------------------------------------- flowers


def floret(x, y, r, w=0.85):
    """One four-petalled osmanthus flower."""
    out = []
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        px, py = x + math.cos(a) * r, y + math.sin(a) * r
        out.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="{f(r*0.62)}" stroke-width="{f(w)}"/>')
    out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r*0.26)}" fill="currentColor" stroke="none"/>')
    return "".join(out)


def flower_cluster(x, y, ang, rng, n=7, r=2.5, spread=6.0, w=0.85):
    """Axillary cluster: florets packed loosely around the axil."""
    out = []
    for i in range(n):
        a = ang + rng.uniform(-1.1, 1.1)
        d = spread * (0.25 + 0.75 * (i / n))
        out.append(floret(x + math.cos(a) * d, y + math.sin(a) * d, r * rng.uniform(0.82, 1.1), w))
    return "".join(out)


def bead(x, y, r, w=1.15):
    """Dew bead clinging to a leaf tip."""
    return (
        f'<path d="M{f(x-r*0.66)} {f(y-r*0.6)} '
        f'C{f(x-r*1.02)} {f(y+r*0.3)} {f(x-r*0.52)} {f(y+r)} {f(x)} {f(y+r)} '
        f'C{f(x+r*0.52)} {f(y+r)} {f(x+r*1.02)} {f(y+r*0.3)} {f(x+r*0.66)} {f(y-r*0.6)} '
        f'Q{f(x)} {f(y-r*0.16)} {f(x-r*0.66)} {f(y-r*0.6)} Z" stroke-width="{f(w)}"/>'
        f'<path d="M{f(x-r*0.42)} {f(y+r*0.16)} a{f(r*0.55)} {f(r*0.55)} 0 0 1 '
        f'{f(r*0.3)} {f(-r*0.42)}" stroke-width="{f(w*0.6)}" opacity="0.7"/>'
    )


# ----------------------------------------------------------------- sprigs


def sprig(pts, rng, leaf_len=26, leaf_w=6.4, flowers=True, dew=(), solid=False, stem_w=2.4):
    """A stem through `pts` (cubic), with opposite leaf pairs at each node."""
    (p0, p1, p2, p3) = pts

    def at(t):
        m = 1 - t
        return (
            m**3 * p0[0] + 3 * m**2 * t * p1[0] + 3 * m * t**2 * p2[0] + t**3 * p3[0],
            m**3 * p0[1] + 3 * m**2 * t * p1[1] + 3 * m * t**2 * p2[1] + t**3 * p3[1],
        )

    def tangent(t):
        m = 1 - t
        dx = 3 * m**2 * (p1[0] - p0[0]) + 6 * m * t * (p2[0] - p1[0]) + 3 * t**2 * (p3[0] - p2[0])
        dy = 3 * m**2 * (p1[1] - p0[1]) + 6 * m * t * (p2[1] - p1[1]) + 3 * t**2 * (p3[1] - p2[1])
        h = math.hypot(dx, dy) or 1
        return dx / h, dy / h

    out = [P(f"M{f(p0[0])} {f(p0[1])} C{f(p1[0])} {f(p1[1])} {f(p2[0])} {f(p2[1])} "
             f"{f(p3[0])} {f(p3[1])}", stem_w)]
    nodes = [0.14, 0.34, 0.54, 0.73, 0.89]
    tips = []
    for i, t in enumerate(nodes):
        x, y = at(t)
        tx, ty = tangent(t)
        base_ang = math.atan2(ty, tx)
        L = leaf_len * (1.0 - 0.42 * t)
        W = leaf_w * (1.0 - 0.42 * t)
        for s in (1, -1):
            a = base_ang + s * (0.92 + rng.uniform(-0.08, 0.08))
            if solid:
                out.append(leaf_solid(x, y, a, L, W))
            else:
                out.append(leaf_outline(x, y, a, L, W))
            tips.append((x + math.cos(a) * L, y + math.sin(a) * L))
        if flowers and i % 2 == 0:
            out.append(flower_cluster(x, y, base_ang + math.pi * 0.5, rng, n=7, r=2.4))
    for idx in dew:
        if idx < len(tips):
            tx_, ty_ = tips[idx]
            out.append(bead(tx_, ty_ + 3.0, 3.0))
    return "".join(out)


# ------------------------------------------------------------------ tree


def osmanthus_tree(seed=7, cx=100, ground=186, crown_c=(100, 88), rx=64, ry=52,
                   nleaf=110, dew_n=6, flowers=18):
    """Whole tree: real trunk, radiating limbs, dense oval evergreen crown."""
    rng = random.Random(seed)
    out = []
    # trunk with a slight lean and a root flare
    out.append(P(f"M{f(cx-4)} {f(ground)} C{f(cx-2)} {f(ground-26)} {f(cx+2)} "
                 f"{f(ground-40)} {f(cx+1)} {f(crown_c[1]+ry*0.55)}", 5.0))
    out.append(P(f"M{f(cx-9)} {f(ground)} q5 -5 5 -12", 1.6, opacity="0.8"))
    out.append(P(f"M{f(cx+8)} {f(ground)} q-4 -5 -4 -11", 1.6, opacity="0.8"))
    # primary limbs fanning into the crown
    limb_tips = []
    for a, ln, w in (
        (-1.57, 46, 3.4), (-1.05, 40, 3.0), (-2.10, 40, 3.0),
        (-0.62, 32, 2.5), (-2.55, 32, 2.5), (-1.30, 42, 2.6), (-1.85, 42, 2.6),
    ):
        bx, by = cx + 1, crown_c[1] + ry * 0.55
        ex, ey = bx + math.cos(a) * ln, by + math.sin(a) * ln
        mx = bx + math.cos(a) * ln * 0.5 - math.sin(a) * ln * 0.12
        my = by + math.sin(a) * ln * 0.5 + math.cos(a) * ln * 0.12
        out.append(P(f"M{f(bx)} {f(by)} Q{f(mx)} {f(my)} {f(ex)} {f(ey)}", w))
        limb_tips.append((ex, ey, a))
        # secondary twigs
        for k in (0.55, 0.8):
            sx = bx + (ex - bx) * k
            sy = by + (ey - by) * k
            for s in (1, -1):
                a2 = a + s * 0.55
                out.append(P(f"M{f(sx)} {f(sy)} l{f(math.cos(a2)*13)} {f(math.sin(a2)*13)}", 1.5))
                limb_tips.append((sx + math.cos(a2) * 13, sy + math.sin(a2) * 13, a2))
    # dense leaf mass: rejection-sample inside the crown ellipse, orient outward
    placed = []
    tries = 0
    while len(placed) < nleaf and tries < nleaf * 30:
        tries += 1
        px = rng.uniform(crown_c[0] - rx, crown_c[0] + rx)
        py = rng.uniform(crown_c[1] - ry, crown_c[1] + ry)
        u = ((px - crown_c[0]) / rx) ** 2 + ((py - crown_c[1]) / ry) ** 2
        if u > 1.0:
            continue
        if min((abs(px - qx) + abs(py - qy)) for qx, qy, _ in placed) < 9 if placed else False:
            continue
        ang = math.atan2(py - crown_c[1], px - crown_c[0]) + rng.uniform(-0.5, 0.5)
        L = 15 + 7 * u + rng.uniform(-2, 2)
        placed.append((px, py, ang))
        out.append(leaf_solid(px, py, ang, L, L * 0.235))
    # flower clusters tucked among the leaves
    for _ in range(flowers):
        px, py, ang = placed[rng.randrange(len(placed))]
        out.append(flower_cluster(px, py, ang, rng, n=5, r=1.9, spread=4.6, w=0.75))
    # dew on the lowest leaf tips only
    low = sorted(placed, key=lambda p: -p[1])[: dew_n * 3]
    rng.shuffle(low)
    for (px, py, ang) in low[:dew_n]:
        L = 20
        out.append(bead(px + math.cos(ang) * L, py + math.sin(ang) * L + 2.4, 2.9, 1.05))
    return "".join(out)


# -------------------------------------------------------------- concepts


def c_sprig():
    rng = random.Random(3)
    return sprig(((36, 184), (28, 116), (74, 56), (154, 26)), rng,
                 leaf_len=30, leaf_w=7.6, dew=(1, 5, 9))


def c_tree():
    return osmanthus_tree(seed=7)


def c_tree_roundel():
    out = ['<circle cx="100" cy="100" r="93" stroke-width="2.6"/>']
    out.append(osmanthus_tree(seed=13, cx=100, ground=176, crown_c=(100, 92),
                              rx=56, ry=46, nleaf=88, dew_n=5, flowers=14))
    return "".join(out)


def c_wreath():
    """桂冠 — two mirrored sprigs; osmanthus wreath, the 折桂 idea."""
    rng = random.Random(29)
    out = []
    for s in (1, -1):
        out.append(f'<g transform="scale({s} 1) translate({0 if s==1 else -200} 0)">')
        out.append(
            sprig(((100, 180), (52, 168), (22, 116), (44, 42)), random.Random(29),
                  leaf_len=25, leaf_w=6.2, dew=(3,) if s == 1 else ())
        )
        out.append("</g>")
    out.append(flower_cluster(100, 172, -1.57, rng, n=9, r=2.6, spread=7.5))
    return "".join(out)


def c_bough():
    """A single bough seen up close: three sprigs off one limb, dew beneath."""
    rng = random.Random(19)
    out = [P("M6 58 C56 40 132 44 194 74", 4.6)]
    for (x, y, pts) in (
        (46, 47, ((46, 47), (40, 20), (66, 6), (96, 14))),
        (104, 48, ((104, 48), (104, 22), (128, 8), (160, 18))),
        (150, 58, ((150, 58), (156, 34), (176, 26), (196, 38))),
    ):
        out.append(sprig(pts, rng, leaf_len=22, leaf_w=5.6, dew=()))
    for (x, y) in ((38, 74), (86, 84), (128, 78), (170, 92)):
        out.append(bead(x, y, 3.2))
    out.append(sprig(((70, 62), (66, 92), (92, 118), (128, 126)), rng,
                     leaf_len=24, leaf_w=6.0, dew=(2, 7)))
    return "".join(out)


def c_leaf_dew():
    """One leaf, one flower cluster, one bead — the quietest, most real cut."""
    rng = random.Random(5)
    out = [P("M34 176 C46 132 74 92 122 54", 3.0)]
    out.append(leaf_outline(58, 130, -0.35, 74, 19.5, w=1.9))
    out.append(leaf_outline(58, 130, -2.15, 44, 12.0, w=1.6))
    out.append(flower_cluster(58, 130, -1.2, rng, n=9, r=3.0, spread=8.5, w=1.0))
    out.append(bead(131, 122, 4.6, 1.5))
    out.append(bead(103, 148, 3.2, 1.2))
    return "".join(out)


CONCEPTS = [
    ("AA", "Osmanthus Sprig", "植物图谱式的一枝桂花：五对对生披针叶（带主脉和上半叶缘细齿），叶腋里三簇四瓣小花，三颗露珠挂在叶尖。", c_sprig()),
    ("BB", "Osmanthus Tree", "整棵桂花：微斜的主干带根盘，七条一级枝散入树冠，110 片实心叶排满椭圆冠形，18 簇花藏在叶间，六颗露珠只挂最下层叶尖。", c_tree()),
    ("CC", "Tree Roundel", "BB 收进封边圆 —— 88 片叶的紧实冠形，当头像/印章用。", c_tree_roundel()),
    ("DD", "桂冠 Wreath", "两枝镜像的桂花围成环 —— 桂冠、折桂。中文语境里直接就是成就的意思，底部一簇花收口。", c_wreath()),
    ("EE", "Bough Study", "近景一根横枝：三枝向上的花叶枝条 + 一枝下垂，枝下四颗将落的露珠。最写生。", c_bough()),
    ("FF", "Leaf & Dew", "极简写实：一大一小两片对生叶、一簇九朵花、两颗露珠。最安静。", c_leaf_dew()),
]

SIZES = [(300, "xl"), (140, "lg"), (64, "md"), (32, "xs")]


def svg(body, px):
    return (
        f'<svg width="{px}" height="{px}" viewBox="0 0 {VB} {VB}" fill="none" '
        f'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


cells = []
for key, name, note, body in CONCEPTS:
    row = "".join(svg(body, px) for px, _ in SIZES)
    inv = f'<div class="inv">{svg(body, 140)}</div>'
    cells.append(
        f'<div class="cell"><div class="row">{row}{inv}</div>'
        f"<h3>{key} · {name}</h3><p>{note}</p></div>"
    )

html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>Logo drafts — round 5 (osmanthus + dew)</title>
<style>
  body {{ margin:0; padding:34px; background:#fffdf8;
         font:13px/1.6 -apple-system,"Helvetica Neue",Arial,sans-serif; color:#16181d; }}
  h1 {{ font-size:19px; margin:0 0 4px; }}
  .lede {{ color:#5a616b; margin:0 0 26px; font-size:13px; max-width:880px; }}
  .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:26px; max-width:1600px; }}
  .cell {{ border:1px solid #eae4d8; border-radius:16px; padding:22px 24px; background:#fff; }}
  .row {{ display:flex; align-items:flex-end; gap:26px; margin-bottom:14px; }}
  h3 {{ margin:0 0 3px; font-size:15px; }}
  p {{ margin:0; font-size:12.5px; color:#5a616b; }}
  svg {{ color:#2f4436; }}
  .inv {{ background:#14201a; border-radius:14px; padding:10px; line-height:0; }}
  .inv svg {{ color:#f0e6cf; }}
</style></head><body>
<h1>Logo drafts — round 5：桂花 + 露水（写生画法）</h1>
<p class="lede">按桂花的真实植物特征画：叶严格对生、革质披针形、上半叶缘有细齿、主脉明显；花是四瓣的小花，簇生在<b>叶腋</b>而不是枝顶；
露水只挂在最下层的叶尖 —— 这是露真正会积的位置。没有海、没有水面、没有把露珠当容器。<br>
每格从左到右：300px · 140px · 64px · 32px · 深底反白（暖白纸底 + 深绿墨，接近植物图谱的配色）。</p>
<div class="grid">{"".join(cells)}</div>
</body></html>
"""

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "osmanthus-concepts.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"wrote osmanthus-concepts.html — {len(html)} bytes, {len(CONCEPTS)} concepts")
