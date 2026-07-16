# Blog Style Guide

Writing and markup conventions for all posts under `blog/`. The post scaffold
lives in `components/blog-template.html` (word count, read time, EN/中文 toggle,
and the styles below are baked in there).

## Highlighted links (cross-references to other posts)

When a post references another post on this site, use the shared "pill"
highlight style instead of a plain `<a>`:

```html
<a class="post-hl" href="https://pengandy.com/blog/2025/llm/"
   target="_blank" rel="noopener">learn more in my other blog post &rarr;</a>
```

Style (already in the template's `<style>` block):

```css
a.post-hl { --hl-color: var(--global-theme-color); font-weight: 600; color: var(--hl-color); background: color-mix(in srgb, var(--hl-color) 14%, transparent); padding: 1px 7px; border-radius: 4px; border-bottom: 2px solid var(--hl-color); text-decoration: none; white-space: nowrap; }
a.post-hl:hover { background: var(--hl-color); color: #fff; text-decoration: none; }
```

Rules:

- The **shape** is fixed for every article: semibold text, tinted pill
  background, 2px bottom border, inverts to solid on hover.
- The **color may vary per article.** Default is the site theme blue
  (`--global-theme-color`). If a post has its own accent palette, override
  `--hl-color` in the post's own `<style>`, e.g.
  `a.post-hl { --hl-color: var(--sd-indigo); }`.
- Older posts use per-post class names for the same style (`ant-hl` in
  `blog/2026/curiosity-driven-builder/`, `sd-hl` in
  `blog/2026/speculativedecoding/`). New posts should use `post-hl`.
- Apply to both the English and 中文 versions of the sentence.

## Person names

- Always wrap person names in `<em>` (italic) — never `<strong>` (bold).
  E.g. `co-founder <em>Ben Mann</em>`.

## Emphasis

- Do **not** bold (`<strong>`) any content unless the author explicitly asks.
- Default to plain text; use `<em>` only for names and light emphasis.

## Reading stats

- Every post header carries word count + read time in `.post-readstats`.
- After publishing or editing, run:

```
python3 scripts/sync_reading_stats.py    # sync blog index cards from post metas
python3 scripts/check_reading_stats.py   # verify consistency
python3 scripts/generate_feed.py         # refresh feed.xml
```
