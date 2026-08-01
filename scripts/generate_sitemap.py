#!/usr/bin/env python3
"""Generate sitemap.html — a classic tree view of every page.

Zero-dependency (stdlib only), following the same conventions as
scripts/generate_feed.py. It scans:

  1. Root pages:  ./<name>.html          -> linked extensionless (/<name>)
  2. Subpages:    <dir>/.../index.html   -> linked with trailing slash
  3. Blog layouts: one representative link per distinct blog layout
     (index, pagination, post, year index, archive, tag, category)

and renders them as a `tree`-command style hierarchy with box-drawing
connectors. Directories that are assets/tooling rather than pages are
skipped. Annotations come from each page's <title> tag (or the layout
name for blog representatives).

Output: sitemap.html at the repository root -> https://pengandy.com/sitemap

Usage:
    python3 scripts/generate_sitemap.py            # write sitemap.html
    python3 scripts/generate_sitemap.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "sitemap.html"

# Root .html files that are not standalone pages.
SKIP_ROOT_FILES = {"sitemap.html"}

# Directories that contain assets/tooling, not pages.
SKIP_DIRS = {
    "assets", "backup", "components", "css", "data", "js", "libs",
    "maps", "node_modules", "scripts", "src", ".github", ".git",
}

# Subdirectories of otherwise-included sections that are not pages.
SKIP_SUBPATHS = {("showcase", "shots")}


def page_title(path: Path) -> str:
    """Extract the <title> of a page, falling back to its path."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return str(path.relative_to(REPO_ROOT))
    m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if m:
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
        if title:
            return title
    return str(path.relative_to(REPO_ROOT))


class Node:
    """A node in the site tree: a page, a directory, or both."""

    def __init__(self, name: str, is_dir: bool = True):
        self.name = name
        self.is_dir = is_dir
        self.href: str | None = None
        self.note: str | None = None
        self.children: dict[str, Node] = {}

    def child(self, name: str, is_dir: bool = True) -> "Node":
        node = self.children.get(name)
        if node is None:
            node = self.children[name] = Node(name, is_dir)
        node.is_dir = node.is_dir or is_dir
        return node

    def insert(self, parts: tuple[str, ...], href: str, note: str,
               is_dir: bool = True) -> None:
        node = self
        for part in parts[:-1]:
            node = node.child(part)
        leaf = node.child(parts[-1], is_dir)
        leaf.href = href
        leaf.note = note


def collect_tree() -> Node:
    root = Node("pengandy.com")

    # 1. Root-level pages.
    for path in sorted(REPO_ROOT.glob("*.html")):
        if path.name in SKIP_ROOT_FILES:
            continue
        if path.stem == "index":
            root.insert(("index.html",), "/", "Home", is_dir=False)
        else:
            root.insert((path.stem,), f"/{path.stem}", page_title(path),
                        is_dir=False)

    # 2. Non-blog subpages (<dir>/.../index.html).
    for path in sorted(REPO_ROOT.glob("**/index.html")):
        parts = path.relative_to(REPO_ROOT).parts[:-1]
        if not parts or parts[0] == "blog" or parts[0] in SKIP_DIRS:
            continue
        if any(parts[: len(s)] == s for s in SKIP_SUBPATHS):
            continue
        root.insert(parts, "/" + "/".join(parts) + "/", page_title(path))

    # 3. Blog: one representative per distinct layout.
    blog = REPO_ROOT / "blog"

    def first(pattern: str, valid) -> Path | None:
        for p in sorted(blog.glob(pattern)):
            if valid(p):
                return p
        return None

    def latest(pattern: str, valid) -> Path | None:
        for p in sorted(blog.glob(pattern), reverse=True):
            if valid(p):
                return p
        return None

    if (blog / "index.html").exists():
        root.insert(("blog",), "/blog/", "Blog index")

    page = latest("page/*/index.html", lambda p: p.parts[-2].isdigit())
    if page:
        n = page.parts[-2]
        root.insert(("blog", "page", n), f"/blog/page/{n}/", "Blog pagination")

    post = latest(
        "*/*/index.html",
        lambda p: re.fullmatch(r"\d{4}", p.parts[-3]) is not None,
    )
    if post:
        year, slug = post.parts[-3], post.parts[-2]
        root.insert(("blog", year, slug), f"/blog/{year}/{slug}/", "Blog post")

    year_idx = latest(
        "*/index.html",
        lambda p: re.fullmatch(r"\d{4}", p.parts[-2]) is not None,
    )
    if year_idx:
        y = year_idx.parts[-2]
        root.insert(("blog", y), f"/blog/{y}/", "Year index")

    archive = latest(
        "archive/*/index.html",
        lambda p: re.fullmatch(r"\d{4}", p.parts[-2]) is not None,
    )
    if archive:
        y = archive.parts[-2]
        root.insert(("blog", "archive", y), f"/blog/archive/{y}/", "Archive")

    tag = first("tag/*/index.html", lambda p: True)
    if tag:
        t = tag.parts[-2]
        root.insert(("blog", "tag", t), f"/blog/tag/{t}/", "Tag")

    category = first("category/*/index.html", lambda p: True)
    if category:
        c = category.parts[-2]
        root.insert(("blog", "category", c), f"/blog/category/{c}/",
                    "Category")

    return root


def render_tree(root: Node) -> str:
    """Render the tree as `tree`-command style HTML lines."""
    lines = [f'<span class="tree-dir">{html.escape(root.name)}/</span>']

    def sort_key(node: Node):
        # Keep index.html first at any level; otherwise alphabetical.
        return (node.name != "index.html", node.name.lower())

    def walk(node: Node, prefix: str) -> None:
        kids = sorted(node.children.values(), key=sort_key)
        for i, kid in enumerate(kids):
            last = i == len(kids) - 1
            conn = "└── " if last else "├── "
            label = html.escape(kid.name) + ("/" if kid.is_dir else "")
            if kid.href:
                label = (f'<a href="{html.escape(kid.href, quote=True)}">'
                         f"{label}</a>")
            else:
                label = f'<span class="tree-dir">{label}</span>'
            note = ""
            if kid.note:
                note = f'  <span class="tree-note"># {html.escape(kid.note)}</span>'
            lines.append(
                f'<span class="tree-line">{html.escape(prefix + conn)}</span>'
                f"{label}{note}"
            )
            walk(kid, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)


def build_page() -> str:
    tree = render_tree(collect_tree())
    return f"""<!DOCTYPE html> 
<!-- Generated by scripts/generate_sitemap.py — do not edit by hand. -->

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-HTV795ZMCP"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-HTV795ZMCP');
</script>

<html lang="en">
   <head>
      <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <title>Sitemap</title>
      <meta name="author" content="Peng, Andy">
      <meta name="description" content="Layout previews for every root page and subpage on pengandy.com.">
      <meta name="keywords" content="Sitemap, Layouts, Preview">
      <meta name="robots" content="noindex">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha256-DF7Zhf293AJxJNTmh5zhoYYIMs2oXitRfBjY+9L//AY=" crossorigin="anonymous">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.2/css/all.min.css" integrity="sha256-CTSx/A06dm1B063156EVh15m6Y67pAjZZaQc89LLSrU=" crossorigin="anonymous">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/jwarby/jekyll-pygments-themes@master/github.css" media id="highlight_theme_light">
      <link rel="stylesheet" href="/assets/css/main.css?0286170e23c3c109f66311d4c1ef1b3b">
      <link rel="canonical" href="https://pengandy.com/sitemap">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/jwarby/jekyll-pygments-themes@master/native.css" media="none" id="highlight_theme_dark">
      <script src="/assets/js/theme.js?96d6b3e1c3604aca8b6134c7afdd5db6" type="text/javascript"></script> <script src="/assets/js/dark_mode.js?9b17307bb950ffa2e34be0227f53558f" type="text/javascript"></script>
      <script src="/assets/js/components.js" defer></script> 
      <link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">
      <link rel="icon" href="/assets/brand/icon-512.png" sizes="512x512" type="image/png">
      <link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png" sizes="180x180">
      <link rel="manifest" href="/site.webmanifest">
   </head>
   <style>
      /* Sitemap page: classic `tree`-command style directory tree. */
      .sitemap-tree {{
        font-family: SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
        font-size: 0.85rem;
        line-height: 1.85;
        margin-top: 1.75rem;
        white-space: pre;
        overflow-x: auto;
      }}
      .sitemap-tree a {{
        color: var(--global-text-color);
      }}
      .sitemap-tree a:hover {{
        color: var(--global-theme-color);
      }}
      .tree-line {{
        color: var(--global-text-color-light);
        opacity: 0.55;
      }}
      .tree-dir {{
        color: var(--global-text-color);
        font-weight: 600;
      }}
      .tree-note {{
        color: var(--global-text-color-light);
        font-size: 0.8rem;
      }}
   </style>
   <body class="fixed-top-nav" data-page="sitemap">
      <div id="navbar-placeholder"></div>
      <div class="container mt-5">
         <div class="post">
            <header class="post-header">
               <h1 class="post-title">Sitemap</h1>
               <p class="post-description">Layout previews — every root page and subpage, one link per layout.</p>
            </header>
            <article>
               <div class="sitemap-tree">
{tree}
               </div>
            </article>
         </div>
      </div>
      <div id="footer-placeholder"></div>
      <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js" integrity="sha256-/xUj+3OJU5yExlq6GSYGSHk7tPXikynS7ogEvDej/m4=" crossorigin="anonymous" type="text/javascript"></script> 
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/js/bootstrap.bundle.min.js" integrity="sha256-fgLAgv7fyCGopR/gBNq2iW3ZKIdqIcyshnUULC4vex8=" crossorigin="anonymous" type="text/javascript"></script> 
      <script src="/assets/js/no_defer.js?d633890033921b33e0ceb13d22340a9c" type="text/javascript"></script> 
      <script defer src="/assets/js/common.js?acdb9690d7641b2f8d40529018c71a01" type="text/javascript"></script>
   </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if sitemap.html is stale")
    args = parser.parse_args()

    content = build_page()

    if args.check:
        current = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else ""
        if current != content:
            print("sitemap.html is stale; run scripts/generate_sitemap.py",
                  file=sys.stderr)
            return 1
        print("sitemap.html is up to date.")
        return 0

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
