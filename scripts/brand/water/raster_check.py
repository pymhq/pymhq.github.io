#!/usr/bin/env python3
"""Raster check: does the water survive the path the favicons actually take?

Browser-scaled SVG in the concept sheet is not the shipped pipeline. The icons
are rendered once at 1024 and downsampled with LANCZOS, which turns sub-pixel
strokes into partial alpha instead of dropping them. This renders the current
mark, WG and WH through exactly that path at 48 / 32 / 16, composites each on
paper and on ink, and writes an 8x nearest-neighbour blow-up to inspect.

    python3 scripts/brand/water/raster_check.py
    open http://127.0.0.1:8123/scripts/brand/water/raster-check.html
"""
from __future__ import annotations

import os

from PIL import Image
from playwright.sync_api import sync_playwright

import water_concepts as wc          # rewrites the concept sheet on import; harmless
import generate_mark as gm

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = (48, 32, 16)
ZOOM = 8
PAPER = (255, 253, 248, 255)
INK_BG = (20, 32, 26, 255)

VARIANTS = [
    ("current", "现状", wc.mark()),
    ("wg", "WG 抬树让水", wc.wg_lifted()),
    ("wh", "WH 水托", wc.wh_water_base()),
]


def flat_svg(body: str, px: int) -> str:
    body = wc.inline_trees(body)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {gm.VB} {gm.VB}" '
            f'width="{px}" height="{px}" fill="none" stroke="{gm.INK}" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
            ).replace('fill="currentColor"', f'fill="{gm.INK}"')


def master(page, body: str) -> Image.Image:
    page.set_content(f'<body style="margin:0;width:1024px;height:1024px">'
                     f'{flat_svg(body, 1024)}</body>')
    page.wait_for_timeout(250)
    path = os.path.join(HERE, ".master.png")
    page.screenshot(path=path, omit_background=True)
    img = Image.open(path).convert("RGBA")
    os.remove(path)
    return img


def on(bg, im):
    out = Image.new("RGBA", im.size, bg)
    out.alpha_composite(im)
    return out


rows = []
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1024, "height": 1024})
    for key, label, body in VARIANTS:
        m = master(page, body)
        cells = []
        for size in SIZES:
            small = m.resize((size, size), Image.LANCZOS)
            ink = sum(px[3] for px in small.convert("RGBA").getdata()) / (255 * size * size)
            for bg, tag in ((PAPER, "paper"), (INK_BG, "ink")):
                name = f"rc-{key}-{size}-{tag}.png"
                on(bg, small).resize((size * ZOOM, size * ZOOM), Image.NEAREST) \
                    .save(os.path.join(HERE, name))
                cells.append((name, f"{size}px · {tag}", f"{ink * 100:.1f}% 覆盖"))
        rows.append((label, cells))
        print(f"  {label}: " + "  ".join(
            f"{s}px ink={sum(px[3] for px in m.resize((s, s), Image.LANCZOS).getdata()) / (255 * s * s) * 100:.1f}%"
            for s in SIZES))
    b.close()

cards = "".join(
    f'<section><h2>{label}</h2><div class="row">' + "".join(
        f'<figure><img src="{n}" width="{16 * ZOOM}" alt=""><figcaption>{t}<br>'
        f'<span>{c}</span></figcaption></figure>' for n, t, c in cells)
    + "</div></section>"
    for label, cells in rows
)

html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>Raster check — 16/32/48 through the shipped pipeline</title>
<style>
  body {{ margin:0; padding:32px; background:#f4f2ec;
         font:13px/1.6 -apple-system,"Helvetica Neue",Arial,sans-serif; color:#16181d; }}
  h1 {{ font-size:18px; margin:0 0 4px; }}
  p.lede {{ color:#5a616b; max-width:860px; margin:0 0 24px; }}
  section {{ background:#fff; border:1px solid #e6e1d6; border-radius:14px;
             padding:16px 20px; margin-bottom:16px; }}
  h2 {{ font-size:15px; margin:0 0 12px; }}
  .row {{ display:flex; gap:18px; flex-wrap:wrap; }}
  figure {{ margin:0; text-align:center; }}
  img {{ image-rendering:pixelated; border:1px solid #ddd8cc; border-radius:4px;
         display:block; }}
  figcaption {{ font-size:11px; color:#5a616b; margin-top:5px; }}
  figcaption span {{ color:#9aa0a8; }}
</style></head><body>
<h1>真实光栅链路下的 16 / 32 / 48px（1024 → LANCZOS，8 倍最近邻放大观察）</h1>
<p class="lede">这是 favicon 实际走的路径，不是浏览器缩放 SVG。每格标的是墨覆盖率（alpha 均值），
可以看出缩小后还剩多少笔画。左三格纸底、右三格深底，对应浅色和深色标签栏。</p>
{cards}
</body></html>
"""
out = os.path.join(HERE, "raster-check.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"wrote {os.path.relpath(out, gm.ROOT)}")
