#!/usr/bin/env python3
"""Generate notes/LP/index.html (minimal md-style page) from data/LPmemo-data.json."""
import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "LPmemo-data.json"
OUT_FILE = ROOT / "notes" / "LP" / "index.html"

TEMPLATE_HEAD = """<!DOCTYPE html>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-HTV795ZMCP"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-HTV795ZMCP');
</script>

<html lang="en">
<head>
   <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
   <meta charset="utf-8">
   <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
   <meta http-equiv="X-UA-Compatible" content="IE=edge">
   <title>LEADERSHIP</title>
   <meta name="author" content="Peng, Andy">
   <meta name="description" content="Leadership.">

   <!-- Open Graph Meta Tags -->
   <meta property="og:title" content="LEADERSHIP">
   <meta property="og:description" content="Leadership.">
   <meta property="og:url" content="https://pengandy.com/notes/LP">
   <meta property="og:type" content="website">

   <!-- Twitter Card Meta Tags -->
   <meta name="twitter:card" content="summary">
   <meta name="twitter:title" content="LEADERSHIP">
   <meta name="twitter:description" content="Leadership.">
   <meta name="twitter:site" content="@pymhq">

   <link rel="canonical" href="https://pengandy.com/notes/LP">
   <link rel="shortcut icon" href="/assets/projects/Peng Andys Logo Symbol.png">

   <style>
      :root {
         --text: #24292f;
         --text-light: #6a737d;
         --border: #e1e4e8;
         --bg: #ffffff;
         --link: #0969da;
         --code-bg: #f6f8fa;
      }

      * {
         margin: 0;
         padding: 0;
         box-sizing: border-box;
      }

      body {
         background: var(--bg);
         color: var(--text);
         font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', Arial, sans-serif;
         line-height: 1.65;
         padding: 2.5rem 1.25rem 4rem;
      }

      .md {
         max-width: 760px;
         margin: 0 auto;
      }

      .md h1 {
         font-size: 1.9rem;
         font-weight: 700;
         padding-bottom: 0.3rem;
         border-bottom: 1px solid var(--border);
         margin-bottom: 0.6rem;
      }

      .md p {
         margin-bottom: 0.9rem;
         color: var(--text);
      }

      .md .tagline {
         color: var(--text-light);
         font-size: 1rem;
         margin-bottom: 1.6rem;
      }

      .md a {
         color: var(--link);
         text-decoration: none;
      }

      .md a:hover {
         text-decoration: underline;
      }

      .md hr {
         border: none;
         border-top: 1px solid var(--border);
         margin: 2.2rem 0;
      }

      .md ul.memo-list {
         list-style: none;
         padding-left: 0;
      }

      .md ul.memo-list li {
         position: relative;
         padding-left: 6.5rem;
         margin-bottom: 0.7rem;
         color: var(--text);
      }

      .md ul.memo-list li .date {
         position: absolute;
         left: 0;
         width: 6rem;
         color: var(--text-light);
         font-family: 'SF Mono', 'Consolas', monospace;
         font-size: 0.82rem;
      }

      footer.md-footer {
         margin-top: 3rem;
         padding-top: 1.2rem;
         border-top: 1px solid var(--border);
         color: var(--text-light);
         font-size: 0.85rem;
      }

      footer.md-footer p {
         margin-bottom: 0.4rem;
      }

      @media (max-width: 600px) {
         body {
            padding: 1.75rem 1rem 3rem;
         }

         .md ul.memo-list li {
            padding-left: 0;
            padding-top: 1.4rem;
         }

         .md ul.memo-list li .date {
            position: static;
            display: block;
            width: auto;
            margin-bottom: 0.2rem;
         }
      }
   </style>
</head>

<body>
   <div class="md">
      <h1># leadership</h1>

      <hr>

      <ul class="memo-list">
"""

TEMPLATE_TAIL = """      </ul>

      <footer class="md-footer">
         <p><a href="https://pengandy.com">pengandy.com</a></p>
      </footer>
   </div>
</body>
</html>
"""


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data["items"]

    lines = []
    for item in items:
        date = html.escape(item["date"])
        title = html.escape(item["title"])
        url = html.escape(item["url"], quote=True)
        lines.append(
            f'         <li><span class="date">{date}</span><a href="{url}" target="_blank" rel="noopener">{title}</a></li>'
        )

    body = "\n".join(lines) + "\n"
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(TEMPLATE_HEAD + body + TEMPLATE_TAIL, encoding="utf-8")
    print(f"Wrote {OUT_FILE} with {len(items)} items")


if __name__ == "__main__":
    main()
