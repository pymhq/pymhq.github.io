# Brand mark — runbook

The site's icon is a桂花 (Osmanthus fragrans) inside a ring, monochrome ink green
`#2f4436`. Everything under `/assets/brand/` is **machine generated** — do not
hand-edit those files. Change parameters here and re-run.

## Files

| Path | What it is |
| --- | --- |
| `generate_mark.py` | Source of truth for `/assets/brand/*`. Draws the mark and writes the SVGs + PNGs. |
| `drafts/osmanthus_concepts.py` | The six osmanthus concepts explored before picking this one (AA–FF). |
| `drafts/lotus_concepts.py` | The six 荷花/莲蓬 alternatives (GG–LL), kept as a live option. |

Draft scripts write a self-contained preview HTML next to themselves; those
outputs are gitignored.

## Regenerate

```bash
# SVGs only — pure Python, no dependencies
python3 scripts/brand/generate_mark.py

# SVGs + PNGs (needs Pillow and Playwright/Chromium)
python3 scripts/brand/generate_mark.py --png

# verify the script still reproduces the committed files, writing nothing
python3 scripts/brand/generate_mark.py --check
```

`--check` compares SHA-256 of freshly generated output against what is on disk,
rasterising into a temp dir so nothing is touched. It exits non-zero on any
difference. All five files currently match byte for byte.

Dependencies for `--png`:

```bash
pip install pillow playwright && playwright install chromium
```

## What gets written

| File | Purpose |
| --- | --- |
| `logo-mark.svg` | Vector master. Carries a `prefers-color-scheme` rule so it flips to `#cfe0d4` in dark tab bars. |
| `logo-mark-flat.svg` | Same geometry with the colour baked in, for embedding and print. |
| `icon-512.png` | Transparent raster fallback — Safari only supports SVG favicons from version 26. |
| `icon-192.png` | Web app manifest. |
| `apple-touch-icon.png` | 180 px, transparent, 6 px inset so iOS's rounded mask never clips the ring. |

No hand-tuned 16/32 px rasters exist on purpose: the browser scales the SVG (or
the 512 PNG) itself, so a single artwork serves every size. Pages reference the
set with four `<link>` tags; see any page's `<head>`, and `/site.webmanifest`.

## Editing the mark

Adjust the constants at the top of `generate_mark.py`:

- `CROWN` — trunk base, crown centre and radii
- `DENSITY` — `nleaf` (112 leaves), `flowers` (18 axillary clusters), `dew_n`
  (6 beads), leaf length, minimum leaf spacing
- `RING` — ring radius and stroke width (7 was chosen over hairline and bold
  variants because it survives downscaling without swallowing the interior)
- `FIT` / `ART_CENTRE` — where the drawing sits inside the ring
- `INK` / `INK_DARK` — the single colour, light and dark
- `MIN_W` — floor on stroke width; hairlines below this disappear when scaled

Then run `--png` and commit both the script and the regenerated assets.

### Two things that will bite you

**The RNG stream is load-bearing.** Leaf positions, flower placement and dew
selection all come from `random.Random(SEED)`. Adding, removing or reordering
any `rng` call shifts everything drawn afterwards. `flower_cluster()` draws two
separate angles for the x and y offsets — not what you would write from scratch,
but it is what produced the shipped artwork, so it is preserved deliberately.
Run `--check` after any edit: if it reports DIFF and you did not intend to change
the drawing, you disturbed the RNG order.

**`ART_BBOX` is measured, not computed.** It is the ink extent of the bare
artwork `(15.12, 17.35, 170.11, 158.65)`, obtained once in a browser via
`getBBox()`, and is used to fit the drawing inside the ring. If you change
`CROWN` or `DENSITY` enough to move the silhouette, re-measure it:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'scripts/brand')
import generate_mark as gm
from playwright.sync_api import sync_playwright
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" fill="none" '
       'stroke="#000"><g id="art">' + gm.artwork() + '</g></svg>')
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.set_content('<body style="margin:0">' + svg + '</body>'); pg.wait_for_timeout(300)
    print(pg.evaluate("()=>{const b=document.getElementById('art').getBBox();"
                      "return [b.x,b.y,b.width,b.height]}"))
    b.close()
PY
```

## Design decisions worth not relitigating

- **Ring, not bare tree.** Without a container the crown breaks into
  disconnected specks below ~32 px; the ring gives a stable outline at any size.
- **One artwork, no simplified tiers.** Tried three redrawn tiers (112 / 56 / 24
  leaves) and rejected it — the detailed drawing downsampled from 1024 px reads
  better than a redrawn small version, and one file is easier to keep honest.
- **Downsample, never rasterise small.** Drawing straight onto a 16 px canvas
  drops every stroke thinner than one device pixel. LANCZOS from a 1024 px
  master keeps them as partial alpha, so detail survives as grey density.
- **16 px is inherently soft** and that is accepted. On Retina displays the tab
  actually requests 32 device pixels, where the mark holds up.
- **A sprig (`drafts/osmanthus_concepts.py`, concept AA) was tested as the icon
  and rejected** — a diagonal line drawing with lots of white space cannot
  survive 256 pixels. It remains a good decorative element above 32 px.
