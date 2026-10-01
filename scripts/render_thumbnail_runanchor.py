#!/usr/bin/env python3
"""Render the Devpost thumbnail (3:2, PNG ≤5 MB) for runanchor.

Reuses the video renderer's palette and fonts so the thumbnail matches the
demo's visual identity. Text stays inside submit/narration-claims.md rows.

Usage:
    uv run --with pillow python3 scripts/render_thumbnail_runanchor.py \
        --out submit/runanchor-thumbnail.png
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from render_demo_video_runanchor import BG, BORDER, CYAN, DIM, GREEN, MONO, DISP, ORANGE, TEXT

W, H = 1200, 800  # Devpost-recommended 3:2


def font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO if mono else DISP, size)


def ctext(d: ImageDraw.ImageDraw, y: int, s: str, f, color=TEXT) -> int:
    bb = d.textbbox((0, 0), s, font=f)
    d.text(((W - (bb[2] - bb[0])) / 2, y), s, font=f, fill=color)
    return y + (bb[3] - bb[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="submit/runanchor-thumbnail.png")
    args = ap.parse_args()

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # title block
    y = ctext(d, 90, "runanchor", font(96), TEXT)
    y = ctext(d, y + 14, "receipts your coding agent can't fake", font(34), DIM)

    # hook
    y = ctext(d, y + 64, 'agents say: "done, tests pass."', font(40, mono=True), TEXT)
    y = ctext(d, y + 18, "who checks?", font(40, mono=True), CYAN)

    # measured strip — the claim the video proves (claims row 5)
    y += 56
    bw, bh, gap = 470, 190, 40
    x1 = (W - bw * 2 - gap) / 2
    for x, fill, t1, t2, t3 in (
        (x1, ORANGE, "evidence review alone", "64%", "sensitivity 7/11"),
        (x1 + bw + gap, GREEN, "evidence + replay + oracle", "100%", "sensitivity 11/11"),
    ):
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=16,
                            fill="#161B22", outline=fill, width=3)
        bb = d.textbbox((0, 0), t1, font=font(24))
        d.text((x + (bw - (bb[2] - bb[0])) / 2, y + 22), t1, font=font(24), fill=DIM)
        bb = d.textbbox((0, 0), t2, font=font(72))
        d.text((x + (bw - (bb[2] - bb[0])) / 2, y + 62), t2, font=font(72), fill=fill)
        bb = d.textbbox((0, 0), t3, font=font(22, mono=True))
        d.text((x + (bw - (bb[2] - bb[0])) / 2, y + 148), t3, font=font(22, mono=True), fill=TEXT)

    ctext(d, y + bh + 30, "measured on live Nebius Sandboxes · 54-item corpus",
          font(22), DIM)
    ctext(d, H - 58, "Nebius × NVIDIA Global AI Hackathon", font(20, mono=True), BORDER)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB, {W}x{H})")


if __name__ == "__main__":
    main()
