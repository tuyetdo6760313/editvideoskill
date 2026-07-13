---
name: video-brand-kit
description: Personal brand defaults and reusable animation recipes for editing talking-head videos with video-use — neon yellow + white brand, curated keyword callouts, circular picture-in-picture with a branded background, and an opening hook. Use this together with the video-use skill whenever editing a video for this creator, instead of re-deriving the style from scratch or asking about it again.
---

# Video Brand Kit

Companion to [video-use](https://github.com/browser-use/video-use). Where video-use's own SKILL.md says "every specific value... is a worked example, not a mandate" — the values in *this* document are the mandate, for this creator specifically. They were arrived at over five rounds of review on a real video; don't re-derive them from first principles, don't re-ask about them, just apply them. Deviate only if the creator explicitly asks for something different for a specific video.

## When this applies

Any video-use editing session for this creator. Read this file right after `video-use/SKILL.md` at session start, before proposing a strategy.

## Brand tokens

- **Accent color:** neon yellow, `RGB(255, 240, 0)` / `#FFF000`
- **Secondary:** white, `RGB(255, 255, 255)`
- **Font:** Segoe UI Bold — `C:\Windows\Fonts\segoeuib.ttf`, index 0. Not Arial — tried first, replaced after direct feedback ("kiểu chữ" reference screenshots used a cleaner modern sans). Use this font for every on-screen text element in a video: keyword callouts, badges, diagram labels, hook title.

## Keyword callouts (replaces continuous subtitles)

Do **not** caption the full transcript. Pick 4-8 short, high-value keyword moments per video — the core value-prop words, timed to land when the concept is spoken (get the payoff word's timestamp, start the reveal ~0.3s before it so the landed frame syncs with the spoken word). Skip moments already covered by a bigger animation (e.g. don't caption "1 tuần" as a keyword tag if there's also a "1 TUẦN" badge animation at that same moment — pick one).

**Do not use a libass/ASS `subtitles` filter with an `Outline` stroke for this — at readable sizes the outline reads as chunky/clashing no matter the color** (tried neon-yellow outline, then black outline, both rejected on review). Instead render each keyword as its own small pre-rendered PNG-sequence overlay clip (same technique as every other animation in this kit): crisp white Segoe UI Bold text on a soft dark semi-transparent rounded plate, **no outline stroke at all**.

Proven parameters (`helpers/keyword_tag.py`):
```python
FONT_SIZE = 40          # not smaller than ~36 or larger than ~46 — "vừa phải, dễ đọc"
PAD_H, PAD_V = 28, 16
RADIUS = 16
PLATE_RGBA = (12, 12, 12, 165)
CENTER_X = 960
CENTER_Y = 995          # low in frame — original default (MarginV=90-equivalent) read as "too high"
REVEAL, FADE = 0.3, 0.3 # seconds, ease_out_cubic in / ease_in_out_cubic out
```
Typical per-tag duration: 1.2–1.5s total (reveal + hold + fade).

## Skin smoothing (default on for this creator's talking-head footage)

Append to the grade filter chain — mild, edge-aware, ~20% strength as requested ("làm mịn nhẹ 20%"):
```
smartblur=lr=1.2:ls=0.3:lt=12.0
```
Full grade string used across every session so far:
```
eq=contrast=1.06:brightness=0.0:saturation=1.0,curves=master='0/0 0.25/0.23 0.75/0.77 1/1',smartblur=lr=1.2:ls=0.3:lt=12.0
```

## Animation overlay sizing rule

- **Short (~under 3s):** small corner badge, positioned so it never covers the speaker's face, subtle scale+fade entrance (cubic easing, never linear). No PiP needed — the badge just floats over the full-frame footage. This was correct from the first attempt, never needed revision.
- **Long (~5s+, e.g. a multi-step diagram):** switch the speaker into a **circular picture-in-picture** on a branded background (recipe below) and give the animation the rest of the frame.

## Circular PiP recipe (fully debugged — use these numbers directly)

This broke twice before landing here. The core bug: the image mask and the ring outline were drawn from two different radii, so the footage always bled past the ring. **The fix that matters most:** derive both from one shared radius.

```python
CX, CY   = 430, 540      # left side, vertically centered — NOT bottom-right (tried, felt
                          # too minor/hidden; the creator wants their face prominent)
IMG_D    = 480            # visible circle diameter — prominent, not a tiny badge
RING_T   = 3               # thin — thicker (6+) reads as "chói" (glaring)
RING_ALPHA = 200            # out of 255 — full 255 also reads as too bright

# THE FIX: ring bbox radius must equal image radius + half the ring thickness,
# so the ring's inner edge is flush with the image's outer edge. No gap, no bleed.
ring_bbox_radius = IMG_D / 2.0 + RING_T / 2.0
```

**Face crop:** be generous. A tight crop (900×900 square from a 1920-wide source) read as "cắt sát quá" (cropped too tight/ugly) on review. Use a wider square, e.g. `crop=1080:1080:420:0` (centered horizontally, full source height) before scaling down to `IMG_D`. Spot-check the crop against 2-3 frames spread across the segment — this creator's selfie framing is consistent enough that a single static crop window works for the whole segment, no per-frame tracking needed.

**Background — must feel like ambient light, not a spotlight on the circle:**
```python
# glow: WIDE and gentle, not concentrated near the circle
max_r = 1500        # px — big
peak_alpha = 20      # low — was 46-50 in earlier attempts, read as a hotspot
blur = 110            # px gaussian blur

# PLUS a flat uniform wash across the whole canvas so the far side isn't bare:
wash = NEON + (10,)   # alpha 10/255 over the entire frame

# grid: soft texture, not crisp lines
grid_alpha_range = (6, 22)   # min..max, fading in from ~30% of frame height down
grid_blur = 0.6                # px — barely-there softening
```
See `helpers/pip_circle.py` for the full, working script (asset generation + ffmpeg compositing command). It writes `bg_temp.png` / `mask_temp.png` / `ring_temp.png` then composites with `alphamerge` + `overlay` — delete the temp PNGs after the final ffmpeg render, keep the script.

## Opening hook

Every video opens with a ~2s kinetic-type reveal of the topic (e.g. "AI EDIT VIDEO" in white, thin neon-yellow underline bar, accent line in neon yellow beneath). **This must be a transparent overlay composited on top of the real opening footage — never a separate opaque title-card segment that plays before a hard cut.** A standalone-segment version was explicitly rejected: "cần bổ sung cùng video chứ không phải che đầu... dòng chảy cùng video mới đúng" (should flow together with the video, not be a separate blocked-off piece).

- Position in the **upper third** of frame (title ~y=140, accent ~y=228 in a 1080-tall frame) so it clears the speaker's face in typical talking-head framing.
- Small soft dark plate behind just the text block (same style as keyword callouts) for legibility over busy live footage — no full-frame background.
- `start_in_output: 0` as an overlay on the very first segment. **Do not** prepend it as its own EDL range/source — that changes total runtime and shifts every other overlay's `start_in_output`, which is an easy mistake to reintroduce.

See `helpers/hook_overlay.py`.

## Fill genuinely empty stretches

After a first cut, scan the transcript for segments with zero animation support and no callout — anything 5s+ with nothing on screen but the raw talking-head footage tends to read as "trống" (bare) on review. Add one short (~1.3-1.5s) keyword tag per such stretch, same soft-plate style as the other callouts. Don't fill every gap — sparse and tasteful, not wall-to-wall graphics. Bonus points for a tag that sets up a later payoff (e.g. tagging "trời đang mưa" early pays off the closing line's callback).

## Deliverable hygiene

Working files (transcripts, EDL, draft renders, debug frames) are fine to create during editing but **do not leave them all sitting next to the final video** — this creator explicitly does not want a cluttered folder of intermediates. After the final render is confirmed good:
- Delete: alternate-version renders, `base*.mp4`, `clips_*/`, debug PNGs, one-off test files, per-frame PNG sequences (keep the generator script, not its output frames).
- Keep: `edl.json`, `project.md` (session log), source transcripts, the animation generator scripts + their final `.mov`/`.mp4` output.
- Always leave exactly one clearly-named finished video easy to find — copy it to the root of the working directory, not buried in an `edit/` subfolder.

## Helper scripts in this kit

- `helpers/keyword_tag.py` — parameterized keyword-callout generator (text, duration → `.mov`)
- `helpers/pip_circle.py` — parameterized circular-PiP + branded-background generator and compositor
- `helpers/hook_overlay.py` — parameterized opening-hook overlay generator
- `helpers/corner_badge.py` — parameterized short corner-badge generator (the "1 TUẦN" pattern)

All four are self-contained Python + Pillow, shell out to `ffmpeg`/`prores_ks` for the alpha-video encode, and follow video-use's own conventions (cubic easing only, never linear; transparent RGBA PNG sequence → ProRes 4444 alpha `.mov`).
