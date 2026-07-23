#!/usr/bin/env python3
"""Round-3 film assets: globe rotation frames, pill-nav scroll shots, creativity re-shoot."""
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


def temp(src, transform, name):
    html = (ROOT / src).read_text()
    html = transform(html)
    p = ROOT / name
    p.write_text(html)
    return p


# ---------- 1. globe rotation frames: Beijing view -> USA view ----------
# initial: projection.rotate([-116.4, -39.9, 0]); target USA: [98, -39]
# travel eastward across the Pacific: lambda -116.4 -> -262 (== +98 mod 360)
N = 10
for i in range(N):
    t = i / (N - 1)
    e = t * t * (3 - 2 * t)  # smoothstep
    lam = -116.4 + (-262 - (-116.4)) * e
    phi = -39.9 + (-39.0 - (-39.9)) * e
    p = temp("visitings.html",
             lambda h, lam=lam, phi=phi: h.replace(
                 "projection.rotate([-116.4, -39.9, 0]);",
                 f"projection.rotate([{lam:.2f}, {phi:.2f}, 0]);"),
             f"__globe{i}.html")
    shoot(f"{BASE}/__globe{i}.html", OUT / f"globe-{i:02d}.png", budget=25000)
    p.unlink()
    print(f"globe-{i:02d} lam={lam:.1f}")

# ---------- 2. publications & service: scrolled shots per TOC section ----------
def scroll_shots(page, sections, prefix):
    for i, sec in enumerate(sections):
        if sec is None:
            js = ""
        else:
            js = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
                  f"var el=document.getElementById('{sec}');"
                  "if(el){el.scrollIntoView({behavior:'instant',block:'start'});"
                  "window.dispatchEvent(new Event('scroll'));}},600);});</script>")
        p = temp(page, lambda h, js=js: h.replace("</body>", js + "</body>", 1), f"__ss{i}.html")
        shoot(f"{BASE}/__ss{i}.html", OUT / f"{prefix}-{i}.png", budget=30000)
        p.unlink()
        print(f"{prefix}-{i} ({sec})")

scroll_shots("publications.html", [None, "papers", "invited-talks", "media-coverage"], "pub")
scroll_shots("service.html", [None, "svc-organizing", "svc-guest-speaker"], "svc")

# ---------- 3. creativity re-shoot: stacked sections, each exactly 1000px ----------
css = """
html{scroll-snap-type:none !important;scroll-behavior:auto !important;}
html,body{overflow:visible !important;height:auto !important;}
.panel-section{min-height:1000px !important;height:1000px !important;overflow:hidden !important;}
.section-inner{opacity:1 !important;transform:none !important;}
.scroll-hint{display:none !important;}
"""
p = temp("creativity.html",
         lambda h: h.replace('loading="lazy"', 'loading="eager"')
                    .replace('preload="none"', 'preload="metadata"')
                    .replace("</head>", f"<style>{css}</style></head>", 1),
         "__cre.html")
shoot(f"{BASE}/__cre.html", OUT / "creativity.png", h=5200, budget=45000)
p.unlink()
im = Image.open(OUT / "creativity.png")
if im.size[1] > 5000:
    im.convert("RGB").crop((0, 0, 1600, 5000)).save(OUT / "creativity.png")
print("creativity:", Image.open(OUT / 'creativity.png').size)

# ---------- 4. maps-wide re-shoot: hide fixed chrome for a seamless cut ----------
base_css = """
html{scroll-snap-type:none !important;scroll-behavior:auto !important;}
#hero,#design,#photo,#reels{display:none !important;}
#maps{min-height:100vh !important;}
.section-inner{opacity:1 !important;transform:none !important;}
.scroll-hint,.home-link,.lang-toggle{display:none !important;}
"""
def mk(css_extra, name, out):
    p = temp("creativity.html",
             lambda h: h.replace("</head>", f"<style>{base_css}{css_extra}</style></head>", 1),
             name)
    shoot(f"{BASE}/{name}", out)
    p.unlink()

mk("", "__m1.html", "/tmp/m1.png")
mk("#maps .pager .pager-panel:first-child{display:none !important;}", "__m2.html", "/tmp/m2.png")
a, b = Image.open("/tmp/m1.png").convert("RGB"), Image.open("/tmp/m2.png").convert("RGB")
canvas = Image.new("RGB", (3200, 1000), "white")
canvas.paste(a, (0, 0)); canvas.paste(b, (1600, 0))
canvas.save(OUT / "maps-wide.png")
print("maps-wide:", canvas.size)
