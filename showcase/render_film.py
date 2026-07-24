#!/usr/bin/env python3
"""Render the site film to a 60fps MP4 via CDP screencast.

Captures timestamped frames from headless Chrome in real time (no dropped
UI animations, no virtual-time deadlocks), then assembles an exact-timing
constant-60fps H.264 with ffmpeg's concat demuxer.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

W, H = 1920, 1080
URL = "http://localhost:8123/showcase/?record=1"
OUT = "showcase-film.mp4"
MAX_SECONDS = 200
TMP = Path("/tmp/film_frames")


def main():
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()

    frames = []  # (index, timestamp)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": W, "height": H})
        cdp = page.context.new_cdp_session(page)

        def on_frame(params):
            i = len(frames)
            (TMP / f"f{i:06d}.jpg").write_bytes(
                __import__("base64").b64decode(params["data"]))
            frames.append((i, params["metadata"]["timestamp"]))
            try:
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            except Exception:
                pass

        cdp.on("Page.screencastFrame", on_frame)
        page.goto(URL, wait_until="load")
        cdp.send("Page.startScreencast", {
            "format": "jpeg", "quality": 92,
            "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})

        t0 = time.time()
        while time.time() - t0 < MAX_SECONDS:
            page.wait_for_timeout(1000)
            done = page.evaluate("window.__filmDone === true")
            el = time.time() - t0
            if int(el) % 15 < 1:
                print(f"  {el:5.0f}s | {len(frames)} frames | done={done}", flush=True)
            if done:
                page.wait_for_timeout(700)  # tail
                break
        cdp.send("Page.stopScreencast")
        browser.close()

    if len(frames) < 100:
        print("too few frames captured:", len(frames))
        return 1

    # concat list with per-frame durations from CDP timestamps
    lines = []
    for k, (i, ts) in enumerate(frames):
        dur = (frames[k + 1][1] - ts) if k + 1 < len(frames) else 0.5
        dur = min(max(dur, 0.001), 5.0)
        lines.append(f"file 'f{i:06d}.jpg'\nduration {dur:.6f}")
    lines.append(f"file 'f{frames[-1][0]:06d}.jpg'")  # concat quirk: repeat last
    (TMP / "list.txt").write_text("\n".join(lines))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(TMP / "list.txt"),
         "-vf", f"fps=60,scale={W}:{H}:flags=lanczos",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        return 1
    print(f"captured {len(frames)} frames -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
