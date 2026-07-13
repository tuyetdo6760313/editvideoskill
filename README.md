# video-brand-kit

Personal brand defaults and reusable animation recipes for editing talking-head videos with [video-use](https://github.com/browser-use/video-use).

This is not a fork of video-use — it's a small companion skill that sits alongside it. `video-use` handles transcription, cutting, grading, and rendering; this kit adds one creator's proven visual style on top: neon yellow + white brand colors, curated keyword callouts instead of full subtitles, a circular picture-in-picture treatment for longer animations, and a branded opening hook.

Everything here came out of five rounds of real review on an actual video — see `SKILL.md` for the exact reasoning behind each choice, not just the final numbers.

## Setup

Requires video-use already installed (ffmpeg, Python, `uv sync` — see video-use's own `install.md`). This kit only needs Pillow, which video-use's `.venv` already has.

```bash
git clone <this-repo> ~/Developer/video-brand-kit
ln -sfn ~/Developer/video-brand-kit ~/.claude/skills/video-brand-kit
```

## Usage

Read `SKILL.md` at the start of a video-use editing session (right after video-use's own `SKILL.md`) and apply its defaults instead of asking about brand style, subtitle treatment, or animation layout from scratch each time.

The four helper scripts in `helpers/` are standalone and callable directly:

```bash
python helpers/keyword_tag.py "EDIT VIDEO" --duration 1.34 -o kw1.mov
python helpers/corner_badge.py "1" "TUẦN" --duration 2.4 -o badge.mov
python helpers/hook_overlay.py "AI EDIT VIDEO" "DEMO TỰ ĐỘNG · TRỰC TIẾP" -o hook.mov
python helpers/pip_circle.py source.mp4 --ss 58.06 --duration 7.2 -o pip.mp4
```

Each outputs a file ready to drop straight into a video-use `edl.json` `overlays` entry (or, for `pip_circle.py`, as a literal `sources` entry).

## What's intentionally not included

No API keys, no `.env`, no project-specific EDLs, transcripts, or rendered video from the session this was extracted from — see `.gitignore`. This repo is the reusable *recipe*, not any one finished video.
