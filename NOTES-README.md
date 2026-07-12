# Notes Pages (formerly "Memo System")

The old dynamic JSON + JS-renderer memo system has been replaced with minimal,
static, markdown-README-styled pages, matching the look of `studio.html`.

## Current Pages

- `/notes/papers` → `notes/papers/index.html` — notable papers (formerly `papermemo.html`)
- `/notes/LP` → `notes/LP/index.html` — leadership insights (formerly `LPmemo.html`)

The old `papermemo.html` and `LPmemo.html` files have been deleted. Any
existing external links/bookmarks to `/papermemo` or `/LPmemo` will now 404.

## Editing the Papers Notes Page

`notes/papers/index.html` is small (14 entries) and is edited directly by hand.
Add a new `<h2 class="year">` group and `<li>` entries following the existing
markup/style.

## Editing the Leadership Notes Page

`notes/LP/index.html` is generated from `data/LPmemo-data.json` via a script,
since it has many entries and is easier to maintain as data.

1. Edit `data/LPmemo-data.json` — add/edit an item:
   ```json
   {
     "date": "December, 2025",
     "title": "Link text",
     "url": "https://example.com"
   }
   ```
2. Regenerate the HTML page:
   ```
   python3 scripts/generate_lp_notes.py
   ```
3. Commit both the JSON and the regenerated `notes/LP/index.html`.

## Style

Both pages share the same minimal, GitHub-README-like visual style as
`studio.html`: system font stack, thin borders under headings, muted
secondary text color, no Bootstrap/table libraries.

## Legacy Files

`memo-template.html`, `assets/js/memo-renderer.js`, and `data/papermemo-data.json`
have been deleted since they are no longer used. `data/LPmemo-data.json` is kept
as the data source for the generator script above.
