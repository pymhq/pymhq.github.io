#!/usr/bin/env python3
"""Round 6: Nelumbo nucifera (荷花 / 莲蓬), naturalistic, with dew.

Botany the shapes follow:
  - leaves are PELTATE (盾状): the petiole joins at the middle of the blade,
    veins radiate from that point, the rim is undulate
  - young leaves stay furled into a cone (卷叶)
  - petioles carry fine prickles
  - the receptacle (莲蓬) is a flat-topped inverted cone pitted with seeds
  - lotus leaves are superhydrophobic, so dew sits ON the blade as near-perfect
    spheres (荷叶效应) instead of hanging off a tip — the opposite of osmanthus
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


def rot_pt(x, y, rot):
    c, s = math.cos(rot), math.sin(rot)
    return x * c - y * s, x * s + y * c


# -------------------------------------------------------------- lotus leaf


def peltate_leaf(cx, cy, rx, ry, rot=0.0, veins=15, ripple=9, amp=0.055,
                 w=2.2, vein_w=0.95, notch=True):
    """Peltate blade: undulate rim, veins radiating from the central attachment."""
    pts = []
    N = 150
    for i in range(N + 1):
        th = 2 * math.pi * i / N
        k = 1 + amp * math.sin(ripple * th + 0.6)
        x, y = rx * k * math.cos(th), ry * k * math.sin(th)
        x, y = rot_pt(x, y, rot)
        pts.append((cx + x, cy + y))
    d = f"M{f(pts[0][0])} {f(pts[0][1])} " + " ".join(
        f"L{f(x)} {f(y)}" for x, y in pts[1:]
    )
    out = [P(d + " Z", w)]
    for i in range(veins):
        th = 2 * math.pi * i / veins + 0.15
        k = 1 + amp * math.sin(ripple * th + 0.6)
        ex, ey = rot_pt(rx * k * math.cos(th), ry * k * math.sin(th), rot)
        mx, my = rot_pt(rx * k * 0.5 * math.cos(th + 0.16),
                        ry * k * 0.5 * math.sin(th + 0.16), rot)
        out.append(
            P(f"M{f(cx)} {f(cy)} Q{f(cx+mx)} {f(cy+my)} {f(cx+ex)} {f(cy+ey)}",
              vein_w, opacity="0.9")
        )
    if notch:  # the sunken centre where the petiole joins
        out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(min(rx,ry)*0.075)}" '
                   f'fill="currentColor" stroke="none"/>')
    return "".join(out)


def furled_leaf(cx, cy, h, wd, rot=0.0, w=2.0):
    """Young leaf still rolled into a cone."""
    out = []
    p = lambda x, y: tuple(a + b for a, b in zip((cx, cy), rot_pt(x, y, rot)))
    a1, a2 = p(-wd, -h), p(wd * 0.9, -h * 0.94)
    tip = p(0, 0)
    out.append(P(f"M{f(a1[0])} {f(a1[1])} C{f(p(-wd*0.9, -h*0.4)[0])} "
                 f"{f(p(-wd*0.9,-h*0.4)[1])} {f(p(-wd*0.35,-h*0.1)[0])} "
                 f"{f(p(-wd*0.35,-h*0.1)[1])} {f(tip[0])} {f(tip[1])}", w))
    out.append(P(f"M{f(a2[0])} {f(a2[1])} C{f(p(wd*0.85, -h*0.4)[0])} "
                 f"{f(p(wd*0.85,-h*0.4)[1])} {f(p(wd*0.3,-h*0.1)[0])} "
                 f"{f(p(wd*0.3,-h*0.1)[1])} {f(tip[0])} {f(tip[1])}", w))
    # the rolled lip across the top
    out.append(P(f"M{f(a1[0])} {f(a1[1])} C{f(p(-wd*0.3,-h*1.12)[0])} "
                 f"{f(p(-wd*0.3,-h*1.12)[1])} {f(p(wd*0.4,-h*1.1)[0])} "
                 f"{f(p(wd*0.4,-h*1.1)[1])} {f(a2[0])} {f(a2[1])}", w * 0.85))
    out.append(P(f"M{f(p(-wd*0.15,-h*0.98)[0])} {f(p(-wd*0.15,-h*0.98)[1])} "
                 f"q{f(wd*0.3)} {f(h*0.1)} {f(wd*0.05)} {f(h*0.26)}", w * 0.6,
                 opacity="0.85"))
    return "".join(out)


def dew_spheres(cx, cy, rx, ry, rot, rng, n=5, rmin=2.2, rmax=4.6):
    """Beads rolling on the blade — spheres, because the leaf never wets."""
    out = []
    for _ in range(n):
        th = rng.uniform(0, 2 * math.pi)
        k = rng.uniform(0.18, 0.74)
        x, y = rot_pt(rx * k * math.cos(th), ry * k * math.sin(th), rot)
        r = rng.uniform(rmin, rmax)
        out.append(f'<circle cx="{f(cx+x)}" cy="{f(cy+y)}" r="{f(r)}" stroke-width="1.15"/>')
        out.append(P(f"M{f(cx+x-r*0.45)} {f(cy+y+r*0.12)} a{f(r*0.6)} {f(r*0.6)} 0 0 1 "
                     f"{f(r*0.34)} {f(-r*0.46)}", 0.7, opacity="0.75"))
    return "".join(out)


# --------------------------------------------------------------- receptacle


def seed_pod(cx, cy, rx=26.0, ry=8.5, depth=26.0, seeds=14, w=2.4):
    """莲蓬: flat pitted top, tapering funnel body."""
    out = []
    out.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" '
               f'stroke-width="{f(w)}"/>')
    bw = rx * 0.34
    out.append(P(f"M{f(cx-rx)} {f(cy)} C{f(cx-rx*0.92)} {f(cy+depth*0.55)} "
                 f"{f(cx-bw)} {f(cy+depth*0.82)} {f(cx-bw*0.7)} {f(cy+depth)}", w))
    out.append(P(f"M{f(cx+rx)} {f(cy)} C{f(cx+rx*0.92)} {f(cy+depth*0.55)} "
                 f"{f(cx+bw)} {f(cy+depth*0.82)} {f(cx+bw*0.7)} {f(cy+depth)}", w))
    out.append(P(f"M{f(cx-bw*0.7)} {f(cy+depth)} q{f(bw*0.7)} {f(depth*0.16)} "
                 f"{f(bw*1.4)} 0", w))
    # seed pits: concentric rings scaled into the top ellipse
    pits = [(0.0, 0.0)]
    for ring, cnt in ((0.52, 6), (0.86, 8)):
        for i in range(cnt):
            a = 2 * math.pi * i / cnt + (0.4 if ring > 0.6 else 0)
            pits.append((ring * math.cos(a), ring * math.sin(a)))
    for (ux, uy) in pits[:seeds + 1]:
        px, py = cx + ux * rx * 0.78, cy + uy * ry * 0.74
        out.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="{f(rx*0.105)}" '
                   f'stroke-width="1.15"/>')
        out.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="{f(rx*0.045)}" '
                   f'fill="currentColor" stroke="none"/>')
    return "".join(out)


# ------------------------------------------------------------------ flower


def lotus_flower(cx, cy, r=30.0, rings=((1.0, 9, 1.0), (0.66, 7, 0.72)), w=2.0):
    """Bloom: layered ovate petals, back rank drawn lighter for depth."""
    out = []
    for (scale, count, op) in reversed(rings):
        for i in range(count):
            t = i / (count - 1)
            a = math.radians(-176 + 152 * t)
            L = r * scale * (0.78 + 0.34 * math.sin(math.pi * t))
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            W = L * 0.3
            tx, ty = cx + dx * L, cy + dy * L
            c1 = (cx + dx * L * 0.3 + nx * W, cy + dy * L * 0.3 + ny * W)
            c2 = (cx + dx * L * 0.78 + nx * W * 0.72, cy + dy * L * 0.78 + ny * W * 0.72)
            c3 = (cx + dx * L * 0.78 - nx * W * 0.72, cy + dy * L * 0.78 - ny * W * 0.72)
            c4 = (cx + dx * L * 0.3 - nx * W, cy + dy * L * 0.3 - ny * W)
            out.append(
                P(f"M{f(cx)} {f(cy)} C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} "
                  f"{f(tx)} {f(ty)} C{f(c3[0])} {f(c3[1])} {f(c4[0])} {f(c4[1])} "
                  f"{f(cx)} {f(cy)} Z", w * scale, opacity=f"{op}")
            )
    return "".join(out)


def petiole(x0, y0, x1, y1, bow=0.14, w=2.6, prickles=9):
    """Long lotus stalk, with the fine prickles it actually has."""
    mx = (x0 + x1) / 2 - (y1 - y0) * bow
    my = (y0 + y1) / 2 + (x1 - x0) * bow
    out = [P(f"M{f(x0)} {f(y0)} Q{f(mx)} {f(my)} {f(x1)} {f(y1)}", w)]
    for i in range(prickles):
        t = 0.12 + 0.76 * i / max(prickles - 1, 1)
        m = 1 - t
        px = m * m * x0 + 2 * m * t * mx + t * t * x1
        py = m * m * y0 + 2 * m * t * my + t * t * y1
        dx = 2 * m * (mx - x0) + 2 * t * (x1 - mx)
        dy = 2 * m * (my - y0) + 2 * t * (y1 - my)
        h = math.hypot(dx, dy) or 1
        nx, ny = -dy / h, dx / h
        s = 1 if i % 2 == 0 else -1
        out.append(P(f"M{f(px)} {f(py)} l{f(nx*s*2.6)} {f(ny*s*2.6)}", 0.8, opacity="0.8"))
    return "".join(out)


# --------------------------------------------------------------- concepts


def c_lotus_sprig():
    """GG — the AA counterpart: one study stem, leaf + pod, dew on the blade."""
    rng = random.Random(3)
    out = [petiole(40, 188, 96, 74, bow=0.15, w=2.8)]
    out.append(peltate_leaf(104, 62, 48, 30, rot=-0.18, veins=15))
    out.append(dew_spheres(104, 62, 48, 30, -0.18, rng, n=6))
    out.append(petiole(48, 188, 150, 132, bow=-0.12, w=2.2, prickles=7))
    out.append(seed_pod(154, 122, rx=21, ry=7, depth=20, seeds=14, w=2.2))
    return "".join(out)


def c_lotus_clump():
    """HH — the BB counterpart: a whole clump, four stems, leaf + bud + pod."""
    rng = random.Random(11)
    out = []
    out.append(petiole(96, 192, 58, 96, bow=0.10, w=2.4, prickles=8))
    out.append(petiole(100, 192, 146, 108, bow=-0.10, w=2.2, prickles=7))
    out.append(petiole(98, 192, 104, 58, bow=0.04, w=2.6, prickles=9))
    out.append(petiole(102, 192, 150, 156, bow=-0.16, w=2.0, prickles=5))
    # back: furled young leaf
    out.append(f'<g opacity="0.75">{furled_leaf(150, 106, 30, 13, rot=0.22)}</g>')
    # main blades
    out.append(peltate_leaf(56, 88, 42, 26, rot=-0.14, veins=14))
    out.append(dew_spheres(56, 88, 42, 26, -0.14, rng, n=5))
    out.append(peltate_leaf(112, 50, 34, 21, rot=0.12, veins=13, w=2.0))
    out.append(dew_spheres(112, 50, 34, 21, 0.12, rng, n=3, rmin=1.8, rmax=3.4))
    # pod on the short stem
    out.append(seed_pod(152, 150, rx=18, ry=6, depth=17, seeds=14, w=2.0))
    return "".join(out)


def c_pod_study():
    """II — 莲蓬 close up, a blade behind it, one bead caught on the rim."""
    rng = random.Random(7)
    out = [petiole(58, 190, 66, 96, bow=0.08, w=2.2, prickles=7)]
    out.append(f'<g opacity="0.6">{peltate_leaf(60, 80, 38, 24, rot=-0.2, veins=13, w=1.8)}</g>')
    out.append(petiole(104, 190, 122, 86, bow=-0.06, w=3.0, prickles=9))
    out.append(seed_pod(124, 74, rx=34, ry=11, depth=32, seeds=14, w=2.6))
    out.append(f'<circle cx="152" cy="82" r="4.2" stroke-width="1.3"/>')
    out.append(P("M148.4 84 a5.4 5.4 0 0 1 3.1 -4.3", 0.8, opacity="0.75"))
    return "".join(out)


def c_leaf_roundel():
    """JJ — the blade seen from directly above IS the roundel; dew inside it."""
    rng = random.Random(19)
    out = [peltate_leaf(100, 96, 88, 88, rot=0.0, veins=18, ripple=13, amp=0.045, w=2.8,
                        vein_w=1.15)]
    out.append(dew_spheres(100, 96, 88, 88, 0.0, rng, n=9, rmin=3.0, rmax=6.4))
    return "".join(out)


def c_bloom_and_pod():
    """KK — bloom and receptacle side by side: the plant's two stages."""
    rng = random.Random(23)
    out = [petiole(70, 192, 66, 96, bow=0.06, w=2.6, prickles=8)]
    out.append(lotus_flower(66, 88, r=42))
    out.append(petiole(120, 192, 146, 112, bow=-0.1, w=2.2, prickles=7))
    out.append(seed_pod(148, 100, rx=22, ry=7.5, depth=21, seeds=14, w=2.2))
    out.append(f'<g opacity="0.55">{peltate_leaf(112, 150, 40, 15, rot=-0.06, veins=13, w=1.7)}</g>')
    out.append(dew_spheres(112, 150, 40, 15, -0.06, rng, n=3, rmin=1.8, rmax=3.0))
    return "".join(out)


def c_minimal():
    """LL — one blade, three beads, a stub of stalk. The favicon candidate."""
    rng = random.Random(31)
    out = [P("M100 186 C96 150 98 132 100 122", 3.4)]
    out.append(peltate_leaf(100, 92, 66, 40, rot=-0.1, veins=13, ripple=9, amp=0.05, w=3.0,
                            vein_w=1.3))
    out.append(dew_spheres(100, 92, 66, 40, -0.1, rng, n=3, rmin=4.2, rmax=6.6))
    return "".join(out)


CONCEPTS = [
    ("GG", "Lotus Sprig", "对应 AA 的写生一枝：盾状叶（叶柄接在叶片正中、放射叶脉、波状叶缘）+ 一支莲蓬，六颗露珠滚在叶面上。叶柄上有荷花真实的细刺。", c_lotus_sprig()),
    ("HH", "Lotus Clump", "对应 BB 的整株：四支叶柄，一大一小两片展开的荷叶、后方一片卷叶（幼叶）、右下一支莲蓬。露珠停在叶面。", c_lotus_clump()),
    ("II", "Pod Study", "莲蓬特写：平顶漏斗 + 14 格莲子，后方半透明一片荷叶，边缘挂一颗露。", c_pod_study()),
    ("JJ", "Leaf Roundel", "俯视的荷叶本身就是封边圆 —— 18 条放射叶脉、波状边缘、九颗大小不一的露珠。圆形不是外框，是叶子。", c_leaf_roundel()),
    ("KK", "Bloom & Pod", "花与蓬并置，植株的两个阶段：16 瓣的花（分两层，后层减淡）+ 莲蓬 + 一片压低的荷叶。", c_bloom_and_pod()),
    ("LL", "One Blade", "极简：一片荷叶、三颗大露珠、一小段叶柄。这版是唯一有机会做 favicon 的。", c_minimal()),
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
<title>Logo drafts — round 6 (lotus + dew)</title>
<style>
  body {{ margin:0; padding:34px; background:#fdfbf6;
         font:13px/1.6 -apple-system,"Helvetica Neue",Arial,sans-serif; color:#16181d; }}
  h1 {{ font-size:19px; margin:0 0 4px; }}
  .lede {{ color:#5a616b; margin:0 0 26px; font-size:13px; max-width:900px; }}
  .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:26px; max-width:1600px; }}
  .cell {{ border:1px solid #e8e2d6; border-radius:16px; padding:22px 24px; background:#fff; }}
  .row {{ display:flex; align-items:flex-end; gap:26px; margin-bottom:14px; }}
  h3 {{ margin:0 0 3px; font-size:15px; }}
  p {{ margin:0; font-size:12.5px; color:#5a616b; }}
  svg {{ color:#2b4a44; }}
  .inv {{ background:#122220; border-radius:14px; padding:10px; line-height:0; }}
  .inv svg {{ color:#f1e8d5; }}
</style></head><body>
<h1>Logo drafts — round 6：荷花 / 莲蓬 + 露水</h1>
<p class="lede">按荷花的真实特征画：叶是<b>盾状</b>的 —— 叶柄接在叶片正中而不是边缘，叶脉从那个点放射出去，叶缘呈波状；幼叶卷成锥形；叶柄带细刺；
莲蓬是平顶漏斗、顶面一格格嵌着莲子。露水的处理和桂花刚好相反：荷叶超疏水（荷叶效应），水在叶面上滚成<b>正球</b>，
所以露珠是停在叶面上的圆珠，不是挂在叶尖的水滴。<br>
每格从左到右：300px · 140px · 64px · 32px · 深底反白。GG 对应 AA、HH 对应 BB，方便直接比。</p>
<div class="grid">{"".join(cells)}</div>
</body></html>
"""

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lotus-concepts.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"wrote lotus-concepts.html — {len(html)} bytes, {len(CONCEPTS)} concepts")
