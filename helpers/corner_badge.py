# -*- coding: utf-8 -*-
"""Short corner-badge generator (video-brand-kit) — the "1 TUẦN" pattern.

For short overlays (~under 3s): a big neon-yellow headline + a smaller
white label beneath, on a soft dark plate, positioned in a corner where
it never covers the speaker's face. Confirmed correct across every
review round — no changes needed since the first version.

Usage:
    python corner_badge.py "1" "TUẦN" --duration 2.4 -o badge.mov
    python corner_badge.py "50%" "NHANH HƠN" --duration 2.4 -o badge.mov --anchor 1700,190
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

NEON = (255, 240, 0)
WHITE = (255, 255, 255)
PLATE_RGBA = (10, 10, 10, 140)

BIG_SIZE = 150
LABEL_SIZE = 46
PAD = 24
RADIUS = 24
SS = 4  # supersample for crisp text / rounded corners

DEFAULT_ANCHOR = (1700, 190)  # upper-right corner, clear of a centered talking-head

REVEAL = 0.4
FADE = 0.4


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def build_badge_layer(big_text: str, label_text: str) -> Image.Image:
    big_font = ImageFont.truetype(FONT_PATH, BIG_SIZE * SS, index=0)
    label_font = ImageFont.truetype(FONT_PATH, LABEL_SIZE * SS, index=0)
    meas = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    big_bbox = meas.textbbox((0, 0), big_text, font=big_font)
    label_bbox = meas.textbbox((0, 0), label_text, font=label_font)
    big_w, big_h = big_bbox[2] - big_bbox[0], big_bbox[3] - big_bbox[1]
    label_w, label_h = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]

    content_w = max(big_w, label_w)
    content_h = big_h + int(8 * SS) + label_h
    pad = PAD * SS
    canvas_w, canvas_h = content_w + pad * 2, content_h + pad * 2

    layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, canvas_w - 1, canvas_h - 1], radius=RADIUS * SS, fill=PLATE_RGBA)

    bx = (canvas_w - big_w) / 2.0 - big_bbox[0]
    by = pad - big_bbox[1]
    d.text((bx, by), big_text, font=big_font, fill=NEON + (255,))

    lx = (canvas_w - label_w) / 2.0 - label_bbox[0]
    ly = pad + big_h + 8 * SS - label_bbox[1]
    d.text((lx, ly), label_text, font=label_font, fill=WHITE + (255,))

    return layer.resize((canvas_w // SS, canvas_h // SS), Image.LANCZOS)


def build(big_text: str, label_text: str, duration: float, out_path: str, anchor: tuple[int, int]) -> None:
    tile = build_badge_layer(big_text, label_text)
    tw, th = tile.size
    ax, ay = anchor
    total_frames = int(round(duration * FPS))

    with tempfile.TemporaryDirectory() as frames_dir:
        for i in range(total_frames):
            t = i / float(FPS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            if t < REVEAL:
                e = ease_out_cubic(clamp01(t / REVEAL))
                scale, alpha = 0.85 + 0.15 * e, e
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
                px, py = int(round(ax - nw / 2.0)), int(round(ay - nh / 2.0))
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
    ap = argparse.ArgumentParser(description="Build a short branded corner badge")
    ap.add_argument("big_text", help="Big neon-yellow headline, e.g. '1'")
    ap.add_argument("label_text", help="Smaller white label beneath, e.g. 'TUẦN'")
    ap.add_argument("--duration", type=float, default=2.4)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--anchor", default="%d,%d" % DEFAULT_ANCHOR, help="cx,cy anchor point")
    args = ap.parse_args()
    cx, cy = (int(v) for v in args.anchor.split(","))
    build(args.big_text, args.label_text, args.duration, args.output, (cx, cy))


if __name__ == "__main__":
    main()
