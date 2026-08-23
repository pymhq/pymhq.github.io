#!/usr/bin/env python3
"""Screenshot one SVG out of maps.html so a drawing can be looked at.

The charts in maps.html are hand-placed SVG: the only check that finds a glyph
sitting on top of a label is a picture of it. This pulls a single <svg> out of
the page, keeps the page's own <style>, and renders it at whatever box the
viewBox asks for.

    python3 scripts/shot_panel.py salish            # panel 2, the hand-drawn chart
    python3 scripts/shot_panel.py salish 550 690 130 200   # a crop, in viewBox units
    python3 scripts/shot_panel.py race
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps.html"

MARKS = {
    "salish": 'aria-label="Illustrated chart of Salish Sea routes',
    "race": 'aria-label="Illustrated chart of Seattle-area race routes',
    "pnw": 'aria-label="Pacific Northwest',
}


def svg_at(html: str, mark: str) -> str:
    i = html.index(mark)
    start = html.rindex("<svg", 0, i)
    end = html.index("</svg>", i) + len("</svg>")
    return html[start:end]


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "salish"
    html = MAPS.read_text()
    svg = svg_at(html, MARKS.get(which, which))
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    if len(sys.argv) > 5:
        vb = [float(v) for v in sys.argv[2:6]]
        svg = re.sub(r'viewBox="[^"]+"', f'viewBox="{" ".join(str(v) for v in vb)}"',
                     svg, count=1)
    scale = min(1800 / vb[2], 1400 / vb[3])
    w, h = round(vb[2] * scale), round(vb[3] * scale)
    style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    page = ROOT / "_shot.html"
    page.write_text("<!doctype html><meta charset=utf-8><style>" + style
                    + f"html,body{{margin:0;background:#f4f6f1}}"
                      f"svg{{display:block;width:{w}px;height:{h}px}}</style>" + svg)
    out = Path(f"/tmp/shot_{which}.png")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        pg.goto(page.as_uri())
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(out))
        b.close()
    page.unlink()
    print(out)
    subprocess.run(["open", str(out)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
