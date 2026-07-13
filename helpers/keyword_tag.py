# -*- coding: utf-8 -*-
"""Keyword-callout overlay generator (video-brand-kit).

Crisp white Segoe UI Bold text on a soft dark rounded plate, no outline
stroke. Renders a transparent RGBA PNG sequence then encodes to a
ProRes 4444 alpha .mov via ffmpeg, ready to drop into a video-use EDL
`overlays` entry.

Usage:
    python keyword_tag.py "EDIT VIDEO" --duration 1.34 -o kw1.mov
    python keyword_tag.py "AI LÀM VIỆC" --duration 1.42 -o kw2.mov --center-y 950
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = r"C:\Windows\Fonts\segoeuib.ttf"
W, H = 1920, 1080
FPS = 24

WHITE = (255, 255, 255)
PLATE_RGBA = (12, 12, 12, 165)

FONT_SIZE = 40
PAD_H, PAD_V = 28, 16
RADIUS = 16

DEFAULT_CENTER_X = 960
DEFAULT_CENTER_Y = 995  # low in frame — see SKILL.md

REVEAL = 0.3
FADE = 0.3


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def render_tile(text: str) -> Image.Image:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE, index=0)
    meas = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bbox = meas.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w, h = tw + 2 * PAD_H, th + 2 * PAD_V
    margin = 8
    tile = Image.new("RGBA", (w + margin * 2, h + margin * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    rect = [margin, margin, w + margin, h + margin]
    d.rounded_rectangle(rect, radius=RADIUS, fill=PLATE_RGBA)
    tx = margin + PAD_H - bbox[0]
    ty = margin + PAD_V - bbox[1]
    d.text((tx, ty), text, font=font, fill=WHITE + (255,))
    return tile


def build(text: str, duration: float, out_path: str, center_x: int, center_y: int) -> None:
    tile = render_tile(text)
    tw, th = tile.size
    total_frames = int(round(duration * FPS))

    with tempfile.TemporaryDirectory() as frames_dir:
        for i in range(total_frames):
            t = i / float(FPS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            if t < REVEAL:
                e = ease_out_cubic(clamp01(t / REVEAL))
                scale, alpha = 0.9 + 0.1 * e, e
            elif t > duration - FADE:
                e = ease_in_out_cubic(clamp01((t - (duration - FADE)) / FADE))
                scale, alpha = 1.0, 1.0 - e
            else:
                scale, alpha = 1.0, 1.0

            if alpha > 0.0:
                nw, nh = max(1, int(round(tw * scale))), max(1, int(round(th * scale)))
                scaled = tile.resize((nw, nh), Image.LANCZOS)
                if alpha < 0.999:
                    r, g, b, a = scaled.split()
                    a = a.point(lambda p, m=alpha: int(p * m))
                    scaled = Image.merge("RGBA", (r, g, b, a))
                px = int(round(center_x - nw / 2.0))
                py = int(round(center_y - nh / 2.0))
                canvas.alpha_composite(scaled, (px, py))

            canvas.save(os.path.join(frames_dir, "f_%04d.png" % i))

        cmd = [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", os.path.join(frames_dir, "f_%04d.png"),
            "-c:v", "prores_ks", "-profile:v", "4444",
            "-pix_fmt", "yuva444p10le", "-r", str(FPS),
            out_path,
        ]
        subprocess.run(cmd, check=True)

    print("wrote", out_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a branded keyword-callout overlay clip")
    ap.add_argument("text", help="Text to display (e.g. 'EDIT VIDEO')")
    ap.add_argument("--duration", type=float, required=True, help="Total clip duration in seconds")
    ap.add_argument("-o", "--output", required=True, help="Output .mov path")
    ap.add_argument("--center-x", type=int, default=DEFAULT_CENTER_X)
    ap.add_argument("--center-y", type=int, default=DEFAULT_CENTER_Y)
    args = ap.parse_args()
    build(args.text, args.duration, args.output, args.center_x, args.center_y)


if __name__ == "__main__":
    main()
