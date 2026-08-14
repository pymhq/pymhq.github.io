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

# A page that asks search engines to skip it should not be advertised in the
# sitemap either. Keying off the page's own robots meta keeps the two from
# ever disagreeing: marking a page noindex is enough to unlist it, with no
# second edit here. Hand-editing sitemap.html cannot work -- this script
# regenerates it in CI and would put the entry straight back.
NOINDEX_RE = re.compile(
    r"""<meta\s+name=["']robots["']\s+content=["'][^"']*\bnoindex\b""",
    re.IGNORECASE,
)


def is_noindex(path: Path) -> bool:
    try:
        return bool(NOINDEX_RE.search(path.read_text(encoding="utf-8",
                                                     errors="replace")))
    except OSError:
        return False


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
        if is_noindex(path):
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
        if is_noindex(path):
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
    """Render the sitemap inside the site shell.

    Rewritten during the 2026-08 rebuild. The previous version emitted its own
    page with Bootstrap, FontAwesome and main.css; since this file is
    regenerated by CI on every push, leaving it alone would have quietly
    overwritten the redesigned sitemap with the old design on the first deploy.

    The `tree`-command rendering is kept — a directory tree is one of the few
    places a monospace face is doing real work — but the chrome, tokens and
    typography now come from assets/css/shell.css like every other page.
    """
    tree = render_tree(collect_tree())
    return f"""<!DOCTYPE html>
<!-- Generated by scripts/generate_sitemap.py - do not edit by hand. -->
<html lang="en">
   <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Sitemap &middot; Peng, Andy</title>
      <meta name="author" content="Peng, Andy">
      <meta name="description" content="Every page on pengandy.com, one link per layout.">
      <link rel="canonical" href="https://pengandy.com/sitemap">

      <meta property="og:type" content="website">
      <meta property="og:url" content="https://pengandy.com/sitemap">
      <meta property="og:title" content="Sitemap &middot; Peng, Andy">
      <meta property="og:description" content="Every page on pengandy.com, one link per layout.">
      <meta property="og:image" content="https://pengandy.com/assets/brand/icon-512.png">
      <meta name="twitter:card" content="summary_large_image">
      <meta name="twitter:site" content="@pymhq">

      <link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">
      <link rel="icon" href="/assets/brand/icon-512.png" sizes="512x512" type="image/png">
      <link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png" sizes="180x180">
      <link rel="manifest" href="/site.webmanifest">

      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap" rel="stylesheet">

      <link rel="stylesheet" href="/assets/css/shell.css">
      <script src="/assets/js/shell.js" defer></script>

      <script async src="https://www.googletagmanager.com/gtag/js?id=G-HTV795ZMCP"></script>
      <script>
         window.dataLayer = window.dataLayer || [];
         function gtag(){{dataLayer.push(arguments);}}
         gtag('js', new Date());
         gtag('config', 'G-HTV795ZMCP');
      </script>

      <style>
         /* A directory tree is one of the few places monospace earns its keep. */
         .sitemap-tree {{
            font-family: "SF Mono", ui-monospace, Menlo, Consolas, monospace;
            font-size: 0.86rem;
            line-height: 1.9;
            margin-top: clamp(30px, 3.4vw, 52px);
            white-space: pre;
            overflow-x: auto;
            color: var(--ink-2);
         }}
         .sitemap-tree a {{
            color: var(--ink);
            border-bottom: 1px solid transparent;
         }}
         .sitemap-tree a:hover {{
            color: var(--accent);
            border-bottom-color: var(--accent);
         }}
         .tree-line {{ color: var(--ink-3); opacity: 0.5; }}
         .tree-dir  {{ color: var(--ink); font-weight: 600; }}
         .tree-note {{ color: var(--ink-3); font-size: 0.8rem; }}
      </style>
   </head>

   <body data-nav-match="sitemap">
      <a class="skip" href="#main">Skip to content</a>
      <nav class="nav" aria-label="Primary" data-shell-nav></nav>

      <header class="shell page-head">
         <p class="eyebrow">
            <span class="lang-en">Index</span>
            <span class="lang-zh" hidden>索引</span>
         </p>
         <h1 class="page-title">
            <span class="lang-en">Sitemap</span>
            <span class="lang-zh" hidden>站点地图</span>
         </h1>
         <p class="page-lede">
            <span class="lang-en">Every page, one link per layout.</span>
            <span class="lang-zh" hidden>全部页面，每种版式一个入口。</span>
         </p>
      </header>

      <main class="shell" id="main" style="padding-bottom:var(--movement)">
         <div class="sitemap-tree">
{tree}
         </div>
      </main>

      <footer class="foot" data-shell-footer></footer>
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
