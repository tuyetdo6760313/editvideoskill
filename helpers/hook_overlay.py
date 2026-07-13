# -*- coding: utf-8 -*-
"""Opening-hook overlay generator (video-brand-kit).

A ~2s kinetic-type reveal (title, underline bar, accent line) meant to be
composited ON TOP of the real opening footage as a video-use EDL overlay
at start_in_output=0 — never as its own opaque segment before a hard cut
(that was tried and explicitly rejected; it breaks the "flows with the
video" feel and silently shifts every other overlay's timing).

Usage:
    python hook_overlay.py "AI EDIT VIDEO" "DEMO TỰ ĐỘNG  ·  TRỰC TIẾP" -o hook.mov
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_PATH = r"C:\Windows\Fonts\segoeuib.ttf"
W, H = 1920, 1080
FPS = 24

WHITE = (255, 255, 255)
NEON = (255, 240, 0)
PLATE_RGBA = (10, 10, 10, 150)

TITLE_SIZE = 76
ACCENT_SIZE = 30

CX = W // 2
TITLE_CY = 140   # upper third — clears the speaker's face in typical framing
ACCENT_CY = 228
BAR_CY = 190
BAR_HALF_W = 150

PLATE_W, PLATE_H = 620, 190


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def text_tile(text: str, font: ImageFont.FreeTypeFont, color: tuple[int, int, int]) -> Image.Image:
    meas = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bbox = meas.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 6
    tile = Image.new("RGBA", (tw + margin * 2, th + margin * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.text((margin - bbox[0], margin - bbox[1]), text, font=font, fill=color + (255,))
    return tile


def paste_scaled_faded(canvas: Image.Image, tile: Image.Image, cx: float, cy: float, scale: float, alpha: float) -> None:
    if alpha <= 0.0:
        return
    tw, th = tile.size
    nw, nh = max(1, int(round(tw * scale))), max(1, int(round(th * scale)))
    scaled = tile.resize((nw, nh), Image.LANCZOS)
    if alpha < 0.999:
        r, g, b, a = scaled.split()
        a = a.point(lambda p, m=alpha: int(p * m))
        scaled = Image.merge("RGBA", (r, g, b, a))
    px, py = int(round(cx - nw / 2.0)), int(round(cy - nh / 2.0))
    canvas.alpha_composite(scaled, (px, py))


def build(title: str, accent: str, duration: float, out_path: str) -> None:
    total_frames = int(round(duration * FPS))

    title_font = ImageFont.truetype(FONT_PATH, TITLE_SIZE, index=0)
    accent_font = ImageFont.truetype(FONT_PATH, ACCENT_SIZE, index=0)
    title_tile = text_tile(title, title_font, WHITE)
    accent_tile = text_tile(accent, accent_font, NEON)

    plate_big = Image.new("RGBA", (PLATE_W * 3, PLATE_H * 3), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate_big)
    pd.rounded_rectangle([0, 0, PLATE_W * 3 - 1, PLATE_H * 3 - 1], radius=40 * 3, fill=PLATE_RGBA)
    plate_tile = plate_big.resize((PLATE_W, PLATE_H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1))

    title_start, title_end = 0.05, 0.45
    plate_start, plate_end = 0.0, 0.35
    bar_start, bar_end = 0.60, 0.85
    accent_start, accent_end = 0.70, 1.05
    fade_start, fade_end = max(duration - 0.25, title_end), duration

    with tempfile.TemporaryDirectory() as frames_dir:
        for i in range(total_frames):
            t = i / float(FPS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            overall_fade = 1.0
            if t >= fade_start:
                overall_fade = 1.0 - ease_in_out_cubic(clamp01((t - fade_start) / (fade_end - fade_start)))

            if overall_fade > 0.0:
                if t >= plate_start:
                    e = ease_out_cubic(clamp01((t - plate_start) / (plate_end - plate_start)))
                    paste_scaled_faded(canvas, plate_tile, CX, (TITLE_CY + ACCENT_CY) // 2 + 6, 0.94 + 0.06 * e, e * overall_fade)

                if t >= title_start:
                    e = ease_out_cubic(clamp01((t - title_start) / (title_end - title_start)))
                    paste_scaled_faded(canvas, title_tile, CX, TITLE_CY, 0.88 + 0.12 * e, e * overall_fade)

                if t >= bar_start:
                    p = ease_out_cubic(clamp01((t - bar_start) / (bar_end - bar_start)))
                    half_w = BAR_HALF_W * p
                    if half_w > 1:
                        d = ImageDraw.Draw(canvas)
                        a = int(255 * overall_fade)
                        d.line([(CX - half_w, BAR_CY), (CX + half_w, BAR_CY)], fill=NEON + (a,), width=2)

                if t >= accent_start:
                    e = ease_out_cubic(clamp01((t - accent_start) / (accent_end - accent_start)))
                    paste_scaled_faded(canvas, accent_tile, CX, ACCENT_CY, 0.92 + 0.08 * e, e * overall_fade)

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
    ap = argparse.ArgumentParser(description="Build the branded opening-hook overlay")
    ap.add_argument("title", help="Main title text, e.g. 'AI EDIT VIDEO'")
    ap.add_argument("accent", help="Accent line beneath, e.g. 'DEMO TỰ ĐỘNG  ·  TRỰC TIẾP'")
    ap.add_argument("--duration", type=float, default=2.0)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    build(args.title, args.accent, args.duration, args.output)


if __name__ == "__main__":
    main()
