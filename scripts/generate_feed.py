#!/usr/bin/env python3
"""Generate a static RSS 2.0 feed (feed.xml) for the blog.

This is a zero-dependency (stdlib only) script tailored to this site's
hand-authored static HTML. It scans posts that live at:

    blog/<YYYY>/<slug>/index.html

and extracts metadata from each post's <head> plus the "Created in <date>"
line in the body. Archive/listing pages (e.g. blog/index.html,
blog/<YYYY>/index.html, blog/page/N/index.html) are skipped because they do
not match the YYYY/slug/index.html shape.

Output: feed.xml at the repository root -> https://pengandy.com/feed.xml

Usage:
    python3 scripts/generate_feed.py            # write feed.xml
    python3 scripts/generate_feed.py --check    # exit 1 if feed.xml is stale
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE_URL = "https://pengandy.com"
FEED_PATH_ON_SITE = "/feed.xml"
FEED_TITLE = "Puget Sound Journal"
FEED_DESCRIPTION = "Andy Peng's notes on research, products, and technical exploration."
AUTHOR = "Andy Peng"

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
OUTPUT_FILE = REPO_ROOT / "feed.xml"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

RFC822_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
RFC822_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                 "Sep", "Oct", "Nov", "Dec"]


def find_post_files() -> list[Path]:
    """Return post HTML files matching blog/<YYYY>/<slug>/index.html."""
    posts = []
    for path in BLOG_DIR.glob("*/*/index.html"):
        rel = path.relative_to(BLOG_DIR)
        # rel.parts == (year, slug, "index.html")
        year, slug = rel.parts[0], rel.parts[1]
        if re.fullmatch(r"\d{4}", year) and slug and slug != "index.html":
            posts.append(path)
    return posts


def _first_match(patterns: list[str], text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


def _attr(text: str, *, tag: str, key: str, key_val: str, attr: str) -> str | None:
    """Extract an attribute value from a tag, e.g. the content of
    <meta property="og:title" content="..."> while correctly handling values
    that contain the *other* quote character (e.g. an apostrophe).

    The opening quote of the target attribute is captured and backreferenced
    so we read the whole value, not just up to the first stray quote.
    """
    pat = (rf'<{tag}\s+[^>]*?{key}=(["\']){re.escape(key_val)}\1'
           rf'[^>]*?{attr}=(["\'])(.*?)\2')
    m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
    return m.group(3).strip() if m else None


def extract_metadata(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")

    title = (
        _attr(text, tag="meta", key="property", key_val="og:title", attr="content")
        or _first_match([r"<title>(.*?)</title>"], text)
    )

    description = (
        _attr(text, tag="meta", key="property", key_val="og:description", attr="content")
        or _attr(text, tag="meta", key="name", key_val="description", attr="content")
        or ""
    )

    url = (
        _attr(text, tag="link", key="rel", key_val="canonical", attr="href")
        or _attr(text, tag="meta", key="property", key_val="og:url", attr="content")
    )

    image = _attr(text, tag="meta", key="property", key_val="og:image", attr="content")

    # "Created in <date>" — may sit inside a <span class="lang-en"> wrapper.
    date_raw = _first_match([r"Created in\s+([^<]+)"], text)
    pub_date = parse_date(date_raw) if date_raw else None

    # Fall back to a URL derived from the file path.
    if not url:
        rel = path.relative_to(REPO_ROOT).parent.as_posix()
        url = f"{SITE_URL}/{rel}/"

    if not title:
        return None  # not a real post

    if pub_date is None:
        # Last resort: keep the post but date it from the file mtime so the
        # feed stays valid rather than dropping content silently.
        pub_date = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    return {
        "title": html.unescape(title),
        "description": html.unescape(description),
        "url": url,
        "image": image,
        "pub_date": pub_date,
        "source": str(path.relative_to(REPO_ROOT)),
    }


def parse_date(raw: str) -> datetime | None:
    """Parse the various human date formats used across posts.

    Supported: "June 7, 2026", "December 5, 2024", "May, 2025",
    "May 2025", "April 12, 2025". Month-only dates default to day 1.
    """
    raw = raw.strip().rstrip(".")
    # Month Day, Year   e.g. "June 7, 2026" / "April 12, 2025"
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            return datetime(int(m.group(3)), month, int(m.group(2)),
                            tzinfo=timezone.utc)
    # Month, Year  /  Month Year   e.g. "May, 2025" / "May 2025"
    m = re.search(r"([A-Za-z]+),?\s+(\d{4})", raw)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            return datetime(int(m.group(2)), month, 1, tzinfo=timezone.utc)
    return None


def rfc822(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return (f"{RFC822_DAYS[dt.weekday()]}, {dt.day:02d} "
            f"{RFC822_MONTHS[dt.month]} {dt.year} "
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0000")


def build_feed(posts: list[dict]) -> str:
    # Use the newest post date (not wall-clock time) so the feed is stable
    # across runs and only changes when post content changes. This keeps
    # --check meaningful and avoids spurious commits in CI.
    if posts:
        last_build = rfc822(max(p["pub_date"] for p in posts))
    else:
        last_build = rfc822(datetime.now(timezone.utc))
    feed_url = f"{SITE_URL}{FEED_PATH_ON_SITE}"

    items = []
    for p in posts:
        enclosure = ""
        if p["image"]:
            enclosure = (f'\n      <enclosure url="{html.escape(p["image"])}" '
                         f'type="image/png" length="0" />')
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(p['title'])}</title>\n"
            f"      <link>{html.escape(p['url'])}</link>\n"
            f"      <guid isPermaLink=\"true\">{html.escape(p['url'])}</guid>\n"
            f"      <pubDate>{rfc822(p['pub_date'])}</pubDate>\n"
            f"      <description>{html.escape(p['description'])}</description>"
            f"{enclosure}\n"
            "    </item>"
        )

    items_xml = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{html.escape(FEED_TITLE)}</title>\n"
        f"    <link>{SITE_URL}/blog/</link>\n"
        f"    <description>{html.escape(FEED_DESCRIPTION)}</description>\n"
        "    <language>en-us</language>\n"
        f"    <managingEditor>{html.escape(AUTHOR)}</managingEditor>\n"
        f"    <lastBuildDate>{last_build}</lastBuildDate>\n"
        f'    <atom:link href="{feed_url}" rel="self" type="application/rss+xml" />\n'
        f"{items_xml}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate blog RSS feed.xml")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if feed.xml is out of date.")
    args = parser.parse_args()

    files = find_post_files()
    posts = [m for m in (extract_metadata(f) for f in files) if m]
    posts.sort(key=lambda p: p["pub_date"], reverse=True)

    feed_xml = build_feed(posts)

    if args.check:
        current = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else ""
        if current.strip() != feed_xml.strip():
            print("feed.xml is out of date. Run: python3 scripts/generate_feed.py",
                  file=sys.stderr)
            return 1
        print(f"feed.xml is up to date ({len(posts)} posts).")
        return 0

    OUTPUT_FILE.write_text(feed_xml, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(REPO_ROOT)} with {len(posts)} posts.")
    for p in posts:
        print(f"  {p['pub_date'].date()}  {p['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
