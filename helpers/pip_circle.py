# -*- coding: utf-8 -*-
"""Circular picture-in-picture generator (video-brand-kit).

Crops a speaker out of a source video into a circular frame with a thin
neon-yellow ring, on a branded background (even ambient glow + soft grid).
Outputs a single composited .mp4 ready to be used as a video-use EDL
source (grade it like any other segment — this script deliberately does
NOT bake in color grading, so the shared per-segment grade filter applies
uniformly and doesn't double-process).

The one bug that bit us twice: the ring and the image mask must share the
same base radius, or the footage bleeds past the ring. Fixed here by
deriving the ring's bbox from IMG_D + RING_T, never independently.

Usage:
    python pip_circle.py source.mp4 --ss 58.06 --duration 7.2 -o pip.mp4
    python pip_circle.py source.mp4 --ss 58.06 --duration 7.2 -o pip.mp4 \\
        --cx 430 --cy 540 --img-d 480 --crop 1080:1080:420:0
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
NEON = (255, 240, 0)
BASE = (27, 24, 18, 255)
GRID = (50, 45, 32, 255)

DEFAULT_CX, DEFAULT_CY = 430, 540   # left side, vertically centered
DEFAULT_IMG_D = 480
DEFAULT_RING_T = 3
DEFAULT_RING_ALPHA = 200
DEFAULT_CROP = "1080:1080:420:0"     # w:h:x:y on a 1920-wide scaled source — generous, not tight


def build_assets(tmpdir: str, cx: int, cy: int, img_d: int, ring_t: int, ring_alpha: int) -> tuple[str, str, str, int]:
    canvas_d = img_d + ring_t * 4 + 8

    # background: base + WIDE gentle glow + flat uniform wash + soft grid
    bg = Image.new("RGBA", (W, H), BASE)

    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    max_r = 1500
    for i in range(max_r, 0, -8):
        a = int(20 * (1 - i / max_r) ** 2)
        gd.ellipse([cx - i, cy - i, cx + i, cy + i], fill=a)
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    glow_layer = Image.new("RGBA", (W, H), NEON + (0,))
    glow_layer.putalpha(glow)
    bg = Image.alpha_composite(bg, glow_layer)

    wash = Image.new("RGBA", (W, H), NEON + (10,))
    bg = Image.alpha_composite(bg, wash)

    grid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grid_layer)
    horizon = int(H * 0.30)
    step = 60
    for x in range(0, W + 1, step):
        gdraw.line([(x, horizon), (x, H)], fill=GRID[:3] + (22,), width=1)
    for y in range(horizon, H + 1, step):
        frac = (y - horizon) / float(H - horizon)
        a = int(6 + 22 * frac)
        gdraw.line([(0, y), (W, y)], fill=GRID[:3] + (a,), width=1)
    grid_layer = grid_layer.filter(ImageFilter.GaussianBlur(0.6))
    bg = Image.alpha_composite(bg, grid_layer)

    bg_path = os.path.join(tmpdir, "bg.png")
    bg.convert("RGB").save(bg_path)

    # circular mask — EXACTLY the visible image circle
    ss = 4
    mask_big = Image.new("L", (img_d * ss, img_d * ss), 0)
    md = ImageDraw.Draw(mask_big)
    md.ellipse([0, 0, img_d * ss - 1, img_d * ss - 1], fill=255)
    mask = mask_big.resize((img_d, img_d), Image.LANCZOS)
    mask_path = os.path.join(tmpdir, "mask.png")
    mask.save(mask_path)

    # ring — bbox radius derived from the SAME img_d, inner edge flush with the image
    ring_big = Image.new("RGBA", (canvas_d * ss, canvas_d * ss), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_big)
    img_r = img_d / 2.0
    ring_bbox_r = (img_r + ring_t / 2.0) * ss
    c = canvas_d * ss / 2.0
    rd.ellipse(
        [c - ring_bbox_r, c - ring_bbox_r, c + ring_bbox_r, c + ring_bbox_r],
        outline=NEON + (ring_alpha,), width=int(round(ring_t * ss)),
    )
    ring = ring_big.resize((canvas_d, canvas_d), Image.LANCZOS)
    ring_path = os.path.join(tmpdir, "ring.png")
    ring.save(ring_path)

    return bg_path, mask_path, ring_path, canvas_d


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a branded circular PiP composite from a source video")
    ap.add_argument("source", help="Path to the source video")
    ap.add_argument("--ss", type=float, required=True, help="Start time in the source (seconds)")
    ap.add_argument("--duration", type=float, required=True, help="Clip duration (seconds)")
    ap.add_argument("-o", "--output", required=True, help="Output .mp4 path")
    ap.add_argument("--cx", type=int, default=DEFAULT_CX)
    ap.add_argument("--cy", type=int, default=DEFAULT_CY)
    ap.add_argument("--img-d", type=int, default=DEFAULT_IMG_D)
    ap.add_argument("--ring-t", type=int, default=DEFAULT_RING_T)
    ap.add_argument("--ring-alpha", type=int, default=DEFAULT_RING_ALPHA)
    ap.add_argument("--crop", default=DEFAULT_CROP, help="ffmpeg crop w:h:x:y on the 1920-wide-scaled source")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        bg_path, mask_path, ring_path, canvas_d = build_assets(
            tmpdir, args.cx, args.cy, args.img_d, args.ring_t, args.ring_alpha
        )
        overlay_x = args.cx - canvas_d // 2
        overlay_y = args.cy - canvas_d // 2
        mask_offset = args.ring_t * 2 + 4  # matches the canvas_d padding in build_assets

        crop_w, crop_h, crop_x, crop_y = args.crop.split(":")

        filter_complex = (
            f"[0:v]scale=1920:-2,crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={args.img_d}:{args.img_d}[face];"
            f"[face][2:v]alphamerge[facea];"
            f"[1:v][facea]overlay=x={overlay_x + mask_offset}:y={overlay_y + mask_offset}[bg1];"
            f"[bg1][3:v]overlay=x={overlay_x}:y={overlay_y}[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(args.ss), "-i", args.source, "-t", str(args.duration),
            "-loop", "1", "-t", str(args.duration), "-i", bg_path,
            "-loop", "1", "-t", str(args.duration), "-i", mask_path,
            "-loop", "1", "-t", str(args.duration), "-i", ring_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "24",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            args.output,
        ]
        subprocess.run(cmd, check=True)

    print("wrote", args.output)


if __name__ == "__main__":
    main()
