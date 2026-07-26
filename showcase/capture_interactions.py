#!/usr/bin/env python3
"""Capture interaction-shot assets for the site film (wide panel strips + blog post)."""
import subprocess
from pathlib import Path
from PIL import Image

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE = "http://localhost:8123"
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "shots"


def shoot(url, out, w=1600, h=1000, budget=30000):
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size={w},{h}",
        f"--virtual-time-budget={budget}", f"--screenshot={out}", url,
    ], check=True, capture_output=True, timeout=180)


def temp_page(src_name, extra_css, tmp_name):
    html = (ROOT / src_name).read_text()
    html = html.replace('loading="lazy"', 'loading="eager"').replace('preload="none"', 'preload="metadata"')
    html = html.replace("</head>", f"<style>{extra_css}</style></head>", 1)
    p = ROOT / tmp_name
    p.write_text(html)
    return p


def stitch_h(files, out):
    imgs = [Image.open(f).convert("RGB") for f in files]
    W = sum(i.size[0] for i in imgs)
    H = max(i.size[1] for i in imgs)
    canvas = Image.new("RGB", (W, H), "white")
    x = 0
    for i in imgs:
        canvas.paste(i, (x, 0)); x += i.size[0]
    canvas.save(out)
    print(f"{out.name}: {canvas.size}")


# ---- 1. home wide (panel1 + endorsements panel side by side) ----
css = """
.hpanels{width:3200px !important;overflow:hidden !important;}
.hpanel{flex:0 0 1600px !important;width:1600px !important;}
#panel-endorse .endorse-panel-inner{opacity:1 !important;transform:none !important;}
"""
p = temp_page("index.html", css, "__home_wide.html")
shoot(f"{BASE}/__home_wide.html", OUT / "home-wide.png", w=3200, h=1000)
p.unlink()
print("home-wide:", Image.open(OUT / 'home-wide.png').size)

# ---- 2. creativity maps: panel 1 & panel 2 viewport shots ----
base_css = """
html{scroll-snap-type:none !important;scroll-behavior:auto !important;}
#hero,#design,#photo,#reels{display:none !important;}
#maps{min-height:100vh !important;}
.section-inner{opacity:1 !important;transform:none !important;}
.scroll-hint{display:none !important;}
"""
p = temp_page("creativity.html", base_css, "__maps1.html")
shoot(f"{BASE}/__maps1.html", "/tmp/maps_p1.png")
p.unlink()
p = temp_page("creativity.html", base_css + "#maps .pager .pager-panel:first-child{display:none !important;}", "__maps2.html")
shoot(f"{BASE}/__maps2.html", "/tmp/maps_p2.png")
p.unlink()
stitch_h(["/tmp/maps_p1.png", "/tmp/maps_p2.png"], OUT / "maps-wide.png")

# ---- 3. visitings PNW: panel 1 & panel 2 (keep home-link visible) ----
base_css = """
html,body{scroll-snap-type:none !important;}
#globe-container,.stats,.legend,.scroll-cue{display:none !important;}
#globe-section{height:0 !important;min-height:0 !important;overflow:visible !important;}
#pnw-section{opacity:1 !important;transform:none !important;height:100vh !important;}
"""
p = temp_page("maps.html", base_css, "__pnw1.html")
shoot(f"{BASE}/__pnw1.html", "/tmp/pnw_p1.png")
p.unlink()
p = temp_page("maps.html", base_css + ".pnw-pager .pnw-panel:first-child{display:none !important;}", "__pnw2.html")
shoot(f"{BASE}/__pnw2.html", "/tmp/pnw_p2.png")
p.unlink()
stitch_h(["/tmp/pnw_p1.png", "/tmp/pnw_p2.png"], OUT / "pnw-wide.png")

# ---- 4. blog post: curiosity-driven-builder full page ----
shoot(f"{BASE}/blog/2026/curiosity-driven-builder/", OUT / "blogpost.png", h=14000, budget=40000)
im = Image.open(OUT / "blogpost.png").convert("RGB")
w, h = im.size
px = im.load()
def near(a, b, t=6): return all(abs(x - y) <= t for x, y in zip(a, b))
def blank(y):
    ref = px[8, y]
    return all(near(px[x, y], ref) for x in range(0, w, 24))
y = h - 1
while y > 0 and blank(y): y -= 1        # trailing blank
fb = y
while y > 0 and not blank(y): y -= 1    # floating footer
gb = y
while y > 0 and blank(y): y -= 1        # filler
if fb - gb < 400 and gb - y > 600:
    im.crop((0, 0, w, y + 100)).save(OUT / "blogpost.png")
    print(f"blogpost: {h} -> {y+100}")
else:
    print(f"blogpost kept: {h} (footer {fb-gb}, filler {gb-y})")
