#!/usr/bin/env python3
"""Capture full-length screenshots of every standalone page on the site.

Uses system Google Chrome in headless mode with a tall window, then trims
trailing uniform-color rows with PIL. Zero third-party browser deps.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE = "http://localhost:8123"
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)

WIDTH = 1600

# (slug, path, capture_height)  -- index uses 100vh horizontal panels, keep viewport-sized
PAGES = [
    ("home",         "/index.html",        1000),
    ("portfolio",    "/portfolio.html",    12000),
    ("blog",         "/blog/",             12000),
    ("publications", "/publications.html", 12000),
    ("projects",     "/projects.html",     14000),
    ("service",      "/service.html",      8000),
    ("creativity",   "/creativity.html",   12000),
    ("news",         "/news.html",         12000),
    ("endorsements", "/endorsements.html", 10000),
    ("resume",       "/resume/",           14000),
    ("studio",       "/studio.html",       10000),
    ("visitings",    "/maps.html",    1000),
    ("office",       "/office.html",       8000),
]


def capture(slug: str, path: str, height: int) -> Path:
    out = OUT / f"{slug}.png"
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={WIDTH},{height}",
        "--virtual-time-budget=20000",
        f"--screenshot={out}",
        f"{BASE}{path}",
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return out


def trim_bottom(img_path: Path, min_height: int = 900) -> None:
    """Trim trailing rows that match the bottom-most row color (blank filler)."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    px = img.load()

    def row_uniform(y: int, ref) -> bool:
        # Sample every 16px across the row.
        return all(px[x, y] == ref for x in range(0, w, 16))

    ref = px[w // 2, h - 1]
    y = h - 1
    while y > min_height and row_uniform(y, ref):
        y -= 1
    new_h = min(h, y + 80)  # keep a little breathing room
    if new_h < h:
        img.crop((0, 0, w, new_h)).save(img_path)
    print(f"  {img_path.name}: {w}x{h} -> {w}x{new_h}")


def main() -> int:
    failed = []
    for slug, path, height in PAGES:
        print(f"capturing {slug} ({path}) ...")
        try:
            out = capture(slug, path, height)
            if height > 1200:
                trim_bottom(out)
            else:
                print(f"  {out.name}: viewport shot kept as-is")
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}")
            failed.append(slug)
    if failed:
        print("failed pages:", failed)
        return 1
    print("all pages captured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
