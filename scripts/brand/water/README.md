# Water studies — 潺潺流水，向左流

A sandbox for putting flowing water into the osmanthus mark. Nothing here is
wired into the site.

```bash
python3 scripts/brand/water/water_concepts.py
# then, with scripts/serve.py running:
open http://127.0.0.1:8123/scripts/brand/water/water-concepts.html
```

`water_concepts.py` imports `../generate_mark.py` read-only for the ring and the
tree, so `assets/brand/*` cannot change from anything in this folder. Confirm
with `python3 scripts/brand/generate_mark.py --check` after any experiment here.

The preview sheet is gitignored; regenerate it rather than committing it.

## What the studies establish

- Direction has to come from shape, not colour: taper to a point downstream, a
  stone whose wake opens downstream, an eddy curl at the tip, and ripples that
  shorten and thin towards the left. Every concept stacks at least two.
- **The shipped composition has no room for water.** Between the trunk base
  (y≈169) and the inside of the ring (y≈187) there are 18 of the 200 canvas
  units, and the interior is only ±28 wide down there. Anything drawn into that
  slot is a grey smudge by 96px. `WG` and `WH` re-fit the same artwork smaller
  and higher to open a 36-unit band; that, not finer linework, is what makes the
  water survive 48px.
- Stroked ripples inherit `MIN_W` and cannot vanish, but cannot taper either.
  Filled ribbons taper properly and lose their tip below ~32px. Both are in the
  sheet on purpose.

If one of these graduates, the work is to fold the water layer and the new
`FIT` / `ART_CENTRE` into `generate_mark.py`, re-run with `--png`, and commit the
script together with the regenerated assets — the RNG warning in
`../README.md` applies.
