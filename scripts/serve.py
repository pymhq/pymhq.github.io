#!/usr/bin/env python3
"""Local preview server for pengandy.com.

Plain `python3 -m http.server` is not a faithful stand-in for GitHub Pages:
Pages resolves an extensionless request like /portfolio to portfolio.html,
while http.server returns 404. Since both the live homepage and plana link
extensionlessly, reviewing on a bare http.server means clicking through a
page full of dead links.

This adds the two Pages behaviours that matter for review:
  /portfolio   -> portfolio.html
  /resume      -> resume/index.html

Stdlib only, matching the conventions of scripts/*.py.
Port 8123 matches showcase/capture.py's BASE, so the screenshot tooling
works against this server unchanged.

Usage:
    python3 scripts/serve.py [port]
"""

from __future__ import annotations

import functools
import http.server
import os
import socketserver
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8123


class PagesHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + GitHub Pages extensionless resolution."""

    def translate_path(self, path: str) -> str:
        resolved = super().translate_path(path)
        if os.path.exists(resolved):
            return resolved
        # /portfolio -> /portfolio.html
        if not resolved.endswith(("/", ".html")) and os.path.isfile(resolved + ".html"):
            return resolved + ".html"
        return resolved

    def log_message(self, fmt: str, *args) -> None:
        # Keep the console readable: only report non-200s.
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith(("4", "5")):
            super().log_message(fmt, *args)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    handler = functools.partial(PagesHandler, directory=str(REPO_ROOT))

    # Threaded, not the plain TCPServer this started as. HTTP/1.1 keep-alive
    # means a browser holds its connection open after the response, and a
    # single-threaded server then serves nobody else until that socket times
    # out: pages hung mid-load and a second tab could not connect at all.
    # daemon_threads so ctrl-c still exits immediately.
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    print(f"site   -> http://localhost:{port}/")
    print(f"  中文 -> http://localhost:{port}/?lang=zh")
    print(f"\nserving {REPO_ROOT} on :{port}   (ctrl-c to stop)\n")

    try:
        with Server(("", port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
