#!/usr/bin/env python3
"""Fake-scroll captures for pill-nav pages (headless scroll compositing is broken,
so we shift the body upward and pin the TOC instead)."""
import subprocess
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE = "http://localhost:8123"
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "shots"


def fake_scroll(page, scroll, active_idx, out):
    html = (ROOT / page).read_text().replace('loading="lazy"', 'loading="eager"')
    css = f"""
    body{{position:relative;top:-{scroll}px;}}
    .pub-toc{{position:fixed !important;top:58px;left:50%;transform:translateX(-50%);
      width:994px;max-width:calc(100vw - 30px);z-index:1000;}}
    """
    js = f"""<script>
    window.addEventListener('load',function(){{
      setInterval(function(){{
        var links=document.querySelectorAll('.pub-toc a');
        links.forEach(function(a,i){{a.classList.toggle('active', i==={active_idx});}});
      }},200);
    }});
    </script>"""
    tmp = ROOT / "__fs.html"
    tmp.write_text(html.replace("</head>", f"<style>{css}</style></head>", 1)
                       .replace("</body>", js + "</body>", 1))
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=1600,1000",
        "--virtual-time-budget=30000", f"--screenshot={OUT / out}",
        f"{BASE}/__fs.html"], check=True, capture_output=True, timeout=180)
    tmp.unlink()
    print(out, f"(scroll {scroll}, pill {active_idx})")


# publications: books=0(base pub-0 exists), papers, invited-talks, media-coverage
fake_scroll("publications.html", 0,    0, "pub-0.png")
fake_scroll("publications.html", 501,  1, "pub-1.png")
fake_scroll("publications.html", 2121, 3, "pub-2.png")
fake_scroll("publications.html", 5221, 5, "pub-3.png")
# service: mentor=0, organizing, guest-speaker
fake_scroll("service.html", 0,    0, "svc-0.png")
fake_scroll("service.html", 467,  1, "svc-1.png")
fake_scroll("service.html", 1455, 4, "svc-2.png")
