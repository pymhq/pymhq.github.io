#!/usr/bin/env python3
"""Build web derivatives for the /photos collections.

The originals are archive material. Some are files straight off a camera or a
conference CDN in assets/invited-talks, one of them 5456x3632 and 4.6 MB; the
rest live in ~/Pictures and are not committed at all, including two 4897x3266
frames off a Canon R5 and two iPhone HEICs. Serving any of that to a gallery
would push a single page into the tens of megabytes, so the page never
references an original. It references derivatives built here instead.

One entry per source, so the mapping from an archive filename nobody chose to a
slug that says what the frame is stays in version control rather than in the
HTML. Add a row, re-run, and the new collection page has its assets.

    python3 scripts/build_photo_derivatives.py           # only what is missing
    python3 scripts/build_photo_derivatives.py --force   # rebuild everything

Up to two widths per source. 1600 is what the viewer opens on a high-density
display; 800 covers phones and the sheet's three-column grid, where a frame
renders at about 350 CSS px. Both are WebP: the same choice
assets/img/headshot-*.webp already made, and it halves the bytes against the
source JPEGs at a quality nobody can pick out.

Never upscales, and the filename carries the width the file actually is.
uwaisummit2025.jpg is 800x800 and thumbnail22.jpg is 600x375, so for those two
the 1600 target clamps to the source and collapses into one file rather than
inventing pixels and lying about them in a w descriptor. The script prints the
src, srcset and intrinsic size for each slug, so the page states measured
numbers instead of intended ones.

Some frames carry a mask. A conference badge QR encodes registration data, so
the box is blanked at full resolution before anything is resized, which means no
derivative ever contains it and no amount of upscaling brings it back. Boxes are
normalised (x, y, w, h) with a top-left origin, measured with the Vision
framework rather than guessed, and check_photo_masks.py re-runs that detector
over the built files to prove nothing is left to decode.

Camera metadata does not survive. Pillow writes no EXIF unless asked to, so the
derivatives carry no timestamps, no serial numbers and no GPS. That is the right
default for files going onto the public web, and it means a photographer's
credit has to be visible in the caption to exist at all, which is where a credit
belongs.
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: python3 -m pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent

# Target widths, widest first.
WIDTHS = (1600, 800)
QUALITY = 82

# (source, collection, slug). The slug is the public name: year first so the
# directory sorts chronologically, then the occasion. An occasion contributing
# more than one frame takes a trailing letter in the order the frames appear on
# the page; a single-frame occasion takes no letter.
SOURCES: tuple[tuple[str, str, str], ...] = (
    # ---- 2026 ----
    # The RLHF Book Launch for Nathan Lambert's Reinforcement Learning from
    # Human Feedback, at Fremont Brewing's Urban Beer Garden. EXIF on the
    # phone frame reads 10 August 2026, 17:24 local.
    ("~/Pictures/events/2026-rlhf-book-launch-a.jpeg",       "events", "2026-rlhf-book-launch-a"),
    ("~/Pictures/events/2026-rlhf-book-launch-b.heic",              "events", "2026-rlhf-book-launch-b"),

    # MLSys 2026, Bellevue, 17 to 22 May, Hyatt Regency Bellevue. The first
    # frame is the one already published with blog/2026/lunch-with-mattwhite,
    # so its alt text is reused from there rather than reinvented.
    ("assets/blog/lunch-with-mattwhite/lunch-with-matt.png",
     "events", "2026-mlsys-a"),
    ("~/Pictures/events/2026-mlsys-b.jpeg",        "events", "2026-mlsys-b"),

    # MSIS 549 again, two years after the 2024 lecture. Dated from EXIF
    # DateTimeOriginal: 14 March 2026, 17:21 to 17:35 local, across two phones.
    ("~/Pictures/events/2026-uw-msis-549-a.jpg",               "events", "2026-uw-msis-549-a"),
    ("~/Pictures/events/2026-uw-msis-549-b.jpg",               "events", "2026-uw-msis-549-b"),
    ("~/Pictures/events/2026-uw-msis-549-c.jpg",               "events", "2026-uw-msis-549-c"),
    ("~/Pictures/events/2026-uw-msis-549-d.heic",              "events", "2026-uw-msis-549-d"),
    ("~/Pictures/events/2026-uw-msis-549-e.jpg",
     "events", "2026-uw-msis-549-e"),

    # ---- 2025 ----
    # NeurIPS 2025 ran a second city for the first time: Mexico City,
    # 30 November to 5 December, in parallel with San Diego.
    ("~/Pictures/events/2025-neurips-cdmx-a.jpg",
     "events", "2025-neurips-cdmx-a"),
    ("~/Pictures/events/2025-neurips-cdmx-b.jpg",
     "events", "2025-neurips-cdmx-b"),
    ("~/Pictures/events/2025-neurips-cdmx-c.jpg",               "events", "2025-neurips-cdmx-c"),

    # UW AI & Robotics Data Summit, 28 August 2025 by EXIF on the three
    # Sony A7 IV frames. The archive tile from the old site goes last.
    ("~/Pictures/events/2025-uw-ai-robotics-summit-a.jpg",               "events", "2025-uw-ai-robotics-summit-a"),
    ("~/Pictures/events/2025-uw-ai-robotics-summit-b.jpg",               "events", "2025-uw-ai-robotics-summit-b"),
    ("~/Pictures/events/2025-uw-ai-robotics-summit-c.jpg",               "events", "2025-uw-ai-robotics-summit-c"),
    ("~/Pictures/events/2025-uw-ai-robotics-summit-d.jpg",               "events", "2025-uw-ai-robotics-summit-d"),
    ("assets/invited-talks/uwaisummit2025.jpg",      "events", "2025-uw-ai-robotics-summit-e"),

    # ICML 2025, Vancouver Convention Centre, July 2025. Reviewer, per
    # service.html. The generated frame sorts last, as everywhere here.
    ("~/Pictures/events/2025-icml-yvr-a.jpg",      "events", "2025-icml-yvr-a"),
    ("~/Pictures/events/2025-icml-yvr-b.jpg",               "events", "2025-icml-yvr-b"),
    ("~/Pictures/events/2025-icml-yvr-c.jpeg",
     "events", "2025-icml-yvr-c"),

    ("assets/invited-talks/Andy Peng - Banner.png",  "events", "2025-packt-genai-summit"),

    # UW Foster MSIS Mentorship Celebration, 3 June 2025. The three
    # 20250603-* files are a photographer's set (EXIF Artist: MATT HAGEN,
    # Canon EOS R5); the two IMG_* are phone frames from the same evening.
    ("~/Pictures/events/2025-msis-mentorship-a.jpg",
     "events", "2025-msis-mentorship-a"),
    ("~/Pictures/events/2025-msis-mentorship-b.jpg",
     "events", "2025-msis-mentorship-b"),
    ("~/Pictures/events/2025-msis-mentorship-c.jpg",
     "events", "2025-msis-mentorship-c"),
    ("~/Pictures/events/2025-msis-mentorship-d.heic",              "events", "2025-msis-mentorship-d"),
    ("~/Pictures/events/Photos/2025-msis-mentorship-e.heic",       "events", "2025-msis-mentorship-e"),

    # SMILE again, 27 May 2025, on internal transfers. The letters name
    # display order, so reordering the set is a re-slug here rather than an
    # edit to the page: IMG_1376 leads, the d4e8... frame closes.
    ("~/Pictures/events/2025-smile-internal-transfer-a.jpg",               "events", "2025-smile-internal-transfer-a"),
    ("~/Pictures/events/2025-smile-internal-transfer-b.png",               "events", "2025-smile-internal-transfer-b"),
    ("~/Pictures/events/2025-smile-internal-transfer-c.jpg",
     "events", "2025-smile-internal-transfer-c"),

    # ---- 2024 ----
    # Episode artwork for the OnBoard! panel. Generated images, not
    # photographs; the page labels them as such.
    ("~/Pictures/events/2024-onboard-podcast-a.jpeg",
     "events", "2024-onboard-podcast-a"),
    ("~/Pictures/events/2024-onboard-podcast-b.jpeg",
     "events", "2024-onboard-podcast-b"),

    # Dinner With Professionals, hosted by the China Entrepreneur Network at
    # UW Seattle, October 2024. Already in news.html, which dates it.
    ("~/Pictures/events/2024-cen-dwp-a.jpg",
     "events", "2024-cen-dwp-a"),
    ("~/Pictures/events/2024-cen-dwp-b.png",               "events", "2024-cen-dwp-b"),

    # B.E.L.L.E. community panel, 16 November 2024, Capital One Cafe Seattle.
    ("~/Pictures/events/2024-belle-seattle.jpg",               "events", "2024-belle-seattle"),


    # OpenAI Community Meetup Seattle, at Madrona: 999 Third Avenue, 34th
    # floor, per Madrona's own contact page. All three frames carry GPS
    # within that block, and EXIF times run 11:43, 11:49 and 11:56 local on
    # 1 August 2024, which is the order the letters follow.
    ("~/Pictures/events/2024-openai-meetup-seattle-a.heic",              "events", "2024-openai-meetup-seattle-a"),
    ("~/Pictures/events/2024-openai-meetup-seattle-b.heic",              "events", "2024-openai-meetup-seattle-b"),
    ("~/Pictures/events/2024-openai-meetup-seattle-c.heic",              "events", "2024-openai-meetup-seattle-c"),
    ("assets/invited-talks/smile24.JPG",             "events", "2024-smile-genai-panel"),

    # KuberTENes Birthday Bash, 6 June 2024, Google's Bay View office in
    # Mountain View. The venue is named in blog/2025/cncf10yo.
    ("~/Pictures/events/2024-kubertenes-a.png",               "events", "2024-kubertenes-a"),
    ("~/Pictures/events/2024-kubertenes-b.jpeg",
     "events", "2024-kubertenes-b"),
    ("~/Pictures/events/2024-kubertenes-c.jpeg",
     "events", "2024-kubertenes-c"),
    ("~/Pictures/events/2024-kubertenes-d.jpeg",
     "events", "2024-kubertenes-d"),
    ("~/Pictures/events/2024-kubertenes-e.jpeg",
     "events", "2024-kubertenes-e"),
    ("~/Pictures/events/2024-kubertenes-f.jpeg",
     "events", "2024-kubertenes-f"),

    # CVPR 2024, 17 to 21 June, Seattle Convention Center. GPS 47.614 on the
    # phone frame, dated 19 June.
    # The badge QR encodes 88 bytes of registration data. The box is measured in
    # the space the mask is applied in, which is *after* exif_transpose: sips
    # hands Pillow a 4032x3024 PNG still carrying Orientation 6, so the image
    # being masked is the rotated 3024x4032 one. Measuring on the unrotated file
    # put the block in the wrong place and left the code readable.
    # scripts/check_photo_masks.py fails if any built frame decodes again.
    ("~/Pictures/events/2024-cvpr-a.heic",              "events", "2024-cvpr-a",
     ((0.39545, 0.69150, 0.16734, 0.12841),)),
    ("~/Pictures/events/2024-cvpr-b.jpeg",
     "events", "2024-cvpr-b"),

    # UW guest lecture, MSIS 549, April 2024.
    ("~/Pictures/events/2024-uw-msis-549-a.jpeg",         "events", "2024-uw-msis-549-a"),
    ("~/Pictures/events/2024-uw-msis-549-b.jpeg",         "events", "2024-uw-msis-549-b"),
    ("~/Pictures/events/2024-uw-msis-549-c.jpeg",         "events", "2024-uw-msis-549-c"),
    ("~/Pictures/events/2024-uw-msis-549-d.png",               "events", "2024-uw-msis-549-d"),

    # Open Source Summit North America 2024, Seattle Convention Center.
    # EXIF on the two HEICs reads 16 and 18 April 2024, spanning the summit.
    # Badge QR resolving to an Amazon Qualtrics survey with query parameters.
    ("~/Pictures/events/2024-open-source-summit-na-a.heic",              "events", "2024-open-source-summit-na-a",
     ((0.88989, 0.83070, 0.04858, 0.05142),)),
    ("~/Pictures/events/2024-open-source-summit-na-b.heic",              "events", "2024-open-source-summit-na-b"),
    ("~/Pictures/events/2024-open-source-summit-na-c.jpg",               "events", "2024-open-source-summit-na-c"),
    ("~/Pictures/events/2024-open-source-summit-na-d.jpg",
     "events", "2024-open-source-summit-na-d"),
    ("~/Pictures/events/2024-open-source-summit-na-e.jpeg",
     "events", "2024-open-source-summit-na-e"),

    # UW guest lecture, MSIS 547, 2 March 2024 by EXIF on the three HEICs.
    ("~/Pictures/events/2024-uw-msis-547-a.jpeg",         "events", "2024-uw-msis-547-a"),
    ("~/Pictures/events/2024-uw-msis-547-b.heic",              "events", "2024-uw-msis-547-b"),
    ("~/Pictures/events/2024-uw-msis-547-c.heic",              "events", "2024-uw-msis-547-c"),
    ("~/Pictures/events/2024-uw-msis-547-d.heic",              "events", "2024-uw-msis-547-d"),
    ("~/Pictures/events/2024-uw-msis-547-e.jpg",               "events", "2024-uw-msis-547-e"),

    # FlickBloom Tech Talks, 19 July 2025, Foundations in Seattle. The Luma
    # page carries start_at 2025-07-19T17:00Z in America/Los_Angeles.
    ("~/Pictures/events/2025-flickbloom-agents.jpeg",
     "events", "2025-flickbloom-agents"),

    # ---- 2023 ----
    # Women in Tech Regatta, April 2023. The three DSC files are off a Sony
    # a5000 whose clock reads 03:21, so the day is not stated on the page.
    # wit23.JPG from the old site is a fourth, distinct frame of the same set.
    ("~/Pictures/events/2023-women-in-tech-regatta-a.jpg",               "events", "2023-women-in-tech-regatta-a"),
    ("~/Pictures/events/2023-women-in-tech-regatta-b.jpg",               "events", "2023-women-in-tech-regatta-b"),
    ("~/Pictures/events/2023-women-in-tech-regatta-c.jpg",               "events", "2023-women-in-tech-regatta-c"),
    ("assets/invited-talks/wit23.JPG",               "events", "2023-women-in-tech-regatta-d"),

    # KubeCon + CloudNativeCon Europe 2023, Amsterdam, 18 to 21 April. The
    # conference where the owner's CNCF Ambassadorship was announced publicly,
    # per blog/2025/cncf10yo. Photographs first, then the generated frames.
    # The -d frame is CNCF's own, CC BY-NC-SA 2.0, attributed in its credit.
    ("assets/invited-talks/cncf23.jpeg",             "events", "2023-kubecon-eu-a"),
    # An 11-character code, not a URL. Masked for the same reason as the others:
    # a code on a badge is not something to publish at full resolution.
    ("~/Pictures/events/2023-kubecon-eu-b.heic",              "events", "2023-kubecon-eu-b",
     ((0.41270, 0.51190, 0.14550, 0.10758),)),
    ("~/Pictures/events/2023-kubecon-eu-c.jpg",               "events", "2023-kubecon-eu-c"),
    ("~/Pictures/events/2023-kubecon-eu-d.jpg",               "events", "2023-kubecon-eu-d"),
    ("~/Pictures/events/2023-kubecon-eu-e.jpg",
     "events", "2023-kubecon-eu-e"),
    ("~/Pictures/events/2023-kubecon-eu-f.jpg",               "events", "2023-kubecon-eu-f"),
    ("~/Pictures/events/2023-kubecon-eu-g.jpg",               "events", "2023-kubecon-eu-g"),
    ("~/Pictures/events/2023-kubecon-eu-h.jpg",               "events", "2023-kubecon-eu-h"),
    ("~/Pictures/events/2023-kubecon-eu-i.jpg",               "events", "2023-kubecon-eu-i"),
    ("~/Pictures/events/2023-kubecon-eu-j.jpeg",
     "events", "2023-kubecon-eu-j"),
    ("~/Pictures/events/2023-kubecon-eu-k.jpeg",
     "events", "2023-kubecon-eu-k"),
    ("~/Pictures/events/2023-kubecon-eu-l.jpeg",
     "events", "2023-kubecon-eu-l"),
    ("~/Pictures/events/2023-kubecon-eu-m.jpeg",
     "events", "2023-kubecon-eu-m"),
    ("~/Pictures/events/2023-kubecon-eu-n.jpeg",
     "events", "2023-kubecon-eu-n"),
    ("~/Pictures/events/2023-kubecon-eu-o.jpeg",
     "events", "2023-kubecon-eu-o"),
    ("assets/invited-talks/thumbnail05.jpg",         "events", "2023-meet-the-ambassadors"),
    ("assets/invited-talks/cuc23.jpg",               "events", "2023-cuc-meetup"),

    # StaffPlus New York 2023. EXIF on the phone frame reads 16 March 2023,
    # 17:23 New York time: Tanya Reilly signing The Staff Engineer's Path.
    ("~/Pictures/events/2023-staffplus-nyc-a.jpeg",
     "events", "2023-staffplus-nyc-a"),
    ("~/Pictures/events/2023-staffplus-nyc-b.jpeg",
     "events", "2023-staffplus-nyc-b"),
    ("~/Pictures/events/2023-staffplus-nyc-c.heic",               "events", "2023-staffplus-nyc-c"),


    # ---- 2018 ----
    # Kai-Fu Lee's AI Superpowers talk and signing, 27 September 2018. The venue
    # is confirmed by Northwest Asian Weekly: The Collective, a private club in
    # South Lake Union.
    ("~/Pictures/events/2018-kaifu-lee-ai-superpowers.jpeg",
     "events", "2018-kaifu-lee-ai-superpowers"),

    # ---- 2019 ----
    # KubeCon + CloudNativeCon North America 2019, San Diego Convention Center,
    # 18 to 21 November. GPS on the iPhone frame reads 32.708, and
    # blog/2025/cncf10yo calls this the first of ten KubeCons.
    ("~/Pictures/events/2019-kubecon-na-a.jpg",               "events", "2019-kubecon-na-a"),
    ("~/Pictures/events/2019-kubecon-na-b.heic",              "events", "2019-kubecon-na-b"),

    # ---- 2022 ----
    ("assets/invited-talks/kubeconna22.png",         "events", "2022-kubecon-na"),
    ("assets/invited-talks/thumbnail03.jpg",         "events", "2022-dockercon"),
    ("assets/invited-talks/thumbnail22.jpg",         "events", "2022-containers-from-the-couch"),

    # ================================================================
    # teams: colleagues and team photographs, sources in ~/Pictures/teams.
    # ================================================================
    ("~/Pictures/teams/2024-anthropic-bedrock.jpeg",
     "teams", "2024-anthropic-bedrock"),

    # 10 May 2023.
    ("~/Pictures/teams/2023-david-yanacek.jpeg",
     "teams", "2023-david-yanacek"),

    # Moved from the events collection: a team occasion, not a talk. The source
    # still sits in ~/Pictures/events, which is where it arrived.
    ("~/Pictures/events/2023-pi-day.jpeg",            "teams", "2023-pi-day"),
    ("~/Pictures/teams/2023-james-hamilton.jpeg",
     "teams", "2023-james-hamilton"),
    ("~/Pictures/teams/2023-junjie-desmond.jpeg",
     "teams", "2023-junjie-desmond"),

    # Builders Day, 16 September 2022.
    ("~/Pictures/teams/2022-builders-day-a.jpeg",
     "teams", "2022-builders-day-a"),
    ("~/Pictures/teams/2022-builders-day-b.jpeg",
     "teams", "2022-builders-day-b"),
    ("~/Pictures/teams/2022-app-runner-team.jpeg",
     "teams", "2022-app-runner-team"),

    # Alexa AI Health and Wellness, 2019.
    ("~/Pictures/teams/2019-alexa-health-a.jpg",                 "teams", "2019-alexa-health-a"),
    ("~/Pictures/teams/2019-alexa-health-b.jpg",                 "teams", "2019-alexa-health-b"),
    ("~/Pictures/teams/2019-alexa-health-c.jpg",                 "teams", "2019-alexa-health-c"),

    # AWS Payments, the first team. A Facebook export with no EXIF date, so the
    # occasion carries the tenure rather than a day: the internal CV puts the
    # Payments years at Pi Day 2016 to March 2019.
    ("~/Pictures/teams/2016-aws-payments.jpg",
     "teams", "2016-aws-payments"),
)


def resolve(src_rel: str) -> Path:
    """Repo-relative path, or an absolute one for sources outside the repo.

    Frames straight off a phone or a photographer's card live in ~/Pictures and
    are deliberately not committed: the repo carries the derivatives, which are
    a twentieth of the bytes and already stripped of camera metadata.
    """
    if src_rel.startswith(("~", "/")):
        return Path(src_rel).expanduser()
    return ROOT / src_rel


# Extra margin around a detected box, as a fraction of its size. A QR needs its
# quiet zone covered too, and the detector reports the symbol, not the zone.
MASK_PAD = 0.10


def apply_masks(im: "Image.Image", masks) -> "Image.Image":
    """Blank each normalised box with a flat fill, at full resolution.

    Flat fill rather than blur or pixelation: QR carries enough error
    correction that a softened symbol can still decode, and a reader cannot
    tell how much was left behind. A solid block is unambiguous, and it reads
    as a deliberate redaction rather than a compression artefact.
    """
    if not masks:
        return im
    out = im.convert("RGB")
    draw = ImageDraw.Draw(out)
    for x, y, w, h in masks:
        px, py = w * MASK_PAD, h * MASK_PAD
        box = (round((x - px) * out.width), round((y - py) * out.height),
               round((x + w + px) * out.width), round((y + h + py) * out.height))
        box = (max(0, box[0]), max(0, box[1]),
               min(out.width, box[2]), min(out.height, box[3]))
        region = out.crop(box)
        # Mean of what is being covered, so the block sits in the photograph's
        # own tonal range instead of looking like a pasted sticker.
        stat = region.resize((1, 1), Image.BOX).getpixel((0, 0))
        draw.rectangle(box, fill=stat)
    return out


@contextlib.contextmanager
def open_frame(src: Path):
    """Yield a PIL image for any source, including HEIC.

    Pillow has no HEIC decoder without pillow-heif, and adding a compiled
    dependency for two iPhone files is a poor trade. macOS ships sips, which
    decodes HEIC natively, so those are transcoded to a temporary PNG first.
    On a machine without sips the error names the missing tool rather than
    failing inside Pillow.
    """
    try:
        with Image.open(src) as im:
            yield im
            return
    except UnidentifiedImageError:
        pass

    if not shutil.which("sips"):
        raise RuntimeError(
            f"cannot decode {src.name}: Pillow has no codec for it and sips "
            "is not on PATH. Install pillow-heif, or convert the file by hand."
        )

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / (src.stem + ".png")
        subprocess.run(
            ["sips", "-s", "format", "png", str(src), "--out", str(staged)],
            check=True, capture_output=True,
        )
        with Image.open(staged) as im:
            im.load()
            yield im


def build(src_rel: str, collection: str, slug: str, force: bool,
          masks=()) -> list[str]:
    """Write every derivative for one source. Returns lines for the report."""
    src = resolve(src_rel)
    if not src.exists():
        return [f"MISS  {src_rel}"]

    out_dir = ROOT / "assets" / "photos" / collection
    out_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    with open_frame(src) as raw:
        # Phone and DSLR files carry rotation in EXIF rather than in the pixel
        # grid. Without this, wit23.JPG lands on its side in the browser.
        im = ImageOps.exif_transpose(raw)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        # Before any resize, so the box cannot survive in a larger variant.
        im = apply_masks(im, masks)

        # The filename states the width the file actually is, never the width
        # that was asked for. An earlier version named every widest derivative
        # "-1600" whatever the source could give, which put a false w
        # descriptor in the page's srcset: the browser was told a 1200px file
        # was 1600px wide and picked it for displays it could not serve. Two
        # targets that clamp to the same width collapse to one file.
        widths = sorted({min(w, im.width) for w in WIDTHS}, reverse=True)

        made: list[tuple[int, int]] = []
        for width in widths:
            height = round(im.height * width / im.width)
            dst = out_dir / f"{slug}-{width}.webp"
            made.append((width, height))

            if dst.exists() and not force:
                lines.append(f"skip  {dst.relative_to(ROOT)}")
                continue

            frame = im.resize((width, height), Image.LANCZOS)
            frame.save(dst, "WEBP", quality=QUALITY, method=6)
            kb = dst.stat().st_size / 1024
            lines.append(
                f"ok    {dst.relative_to(ROOT)}  {width}x{height}  {kb:.0f} KB"
            )

        # Printed so the page's srcset can be copied rather than guessed at.
        base = f"/assets/photos/{collection}/{slug}"
        srcset = ", ".join(f"{base}-{w}.webp {w}w" for w, _ in made)
        lines.append(f"      src={base}-{made[0][0]}.webp  "
                     f"width={made[0][0]} height={made[0][1]}")
        lines.append(f"      srcset={srcset}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="rebuild derivatives that already exist")
    args = ap.parse_args()

    report: list[str] = []
    for entry in SOURCES:
        src, collection, slug = entry[0], entry[1], entry[2]
        masks = entry[3] if len(entry) > 3 else ()
        report += build(src, collection, slug, args.force, masks)

    print("\n".join(report))
    missing = [ln for ln in report if ln.startswith("MISS")]
    if missing:
        print(f"\n{len(missing)} source(s) missing", file=sys.stderr)
        return 1
    written = len([ln for ln in report if ln.startswith(("ok", "skip"))])
    print(f"\n{len(SOURCES)} source(s), {written} derivative(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
