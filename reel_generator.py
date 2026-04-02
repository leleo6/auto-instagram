"""
reel_generator.py
─────────────────────────────────────────────────────────────────────────────
Automates the creation of a daily 9:16 Instagram Reel by combining:
  - A random background video  (./backgrounds/*.mp4)
  - A random music track       (./music/*.mp3)
  - A random motivational quote (./quotes.txt)

Output: daily_reel.mp4 (1080 x 1920, 10 seconds)

Dependencies:
  pip install moviepy Pillow requests
  sudo pacman -S ttf-dejavu   # for DejaVuSans-Bold font on Arch Linux
"""

import os
import random
import textwrap
import logging
from pathlib import Path

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeOut

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

TARGET_W   = 1080          # Final width  (pixels)
TARGET_H   = 1920          # Final height (pixels)
REEL_DURATION = 10         # Seconds
AUDIO_FADEOUT = 2          # Seconds of fade-out at the end of the audio

BACKGROUNDS_DIR = Path("./backgrounds")
MUSIC_DIR       = Path("./music")
QUOTES_FILE     = Path("./quotes.txt")
OUTPUT_FILE     = Path("./daily_reel.mp4")

# Text styling
FONT_PATH      = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"  # Arch Linux path
FONT_SIZE      = 72
TEXT_COLOR     = "white"
STROKE_COLOR   = "black"
STROKE_WIDTH   = 3
MAX_TEXT_WIDTH = 900        # pixels — wrapping threshold (approx. chars below)
WRAP_WIDTH     = 28         # characters per line (tuned for 72px DejaVuSans-Bold)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ASSET HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def pick_random_file(directory: Path, extensions: tuple[str, ...]) -> Path:
    """Return a random file with one of the given extensions from *directory*."""
    files = [f for f in directory.iterdir() if f.suffix.lower() in extensions]
    if not files:
        raise FileNotFoundError(
            f"No files with extensions {extensions} found in '{directory}'."
        )
    chosen = random.choice(files)
    log.info("Selected %s from %s", chosen.name, directory)
    return chosen


def load_random_quote(quotes_file: Path) -> str:
    """Read *quotes_file* and return one random non-empty line."""
    with quotes_file.open("r", encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        raise ValueError(f"'{quotes_file}' is empty or has no valid lines.")
    quote = random.choice(lines)
    log.info("Selected quote: %r", quote)
    return quote


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def prepare_background(video_path: Path, duration: float) -> VideoFileClip:
    """
    Load a background clip, loop if necessary, trim to *duration*, then
    resize-and-center-crop to TARGET_W × TARGET_H (9:16 portrait).
    """
    clip = VideoFileClip(str(video_path))

    # ── Loop the clip if it is shorter than the desired duration ──────────────
    if clip.duration < duration:
        loops_needed = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops_needed)

    clip = clip.subclipped(0, duration)

    # ── Resize so that the clip covers the full target frame (cover strategy) ─
    clip_ratio   = clip.w / clip.h
    target_ratio = TARGET_W / TARGET_H

    if clip_ratio > target_ratio:
        # Clip is wider than target → scale by height, crop width
        new_h = TARGET_H
        new_w = int(clip.w * TARGET_H / clip.h)
    else:
        # Clip is taller than target → scale by width, crop height
        new_w = TARGET_W
        new_h = int(clip.h * TARGET_W / clip.w)

    resized = clip.resized((new_w, new_h))

    # Centre-crop to exact target dimensions
    x_center = new_w // 2
    y_center = new_h // 2
    cropped  = resized.cropped(
        x1=x_center - TARGET_W // 2,
        y1=y_center - TARGET_H // 2,
        x2=x_center + TARGET_W // 2,
        y2=y_center + TARGET_H // 2,
    )
    log.info("Background prepared: %dx%d → %dx%d", clip.w, clip.h, TARGET_W, TARGET_H)
    return cropped


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def prepare_audio(audio_path: Path, duration: float, fadeout: float) -> AudioFileClip:
    """
    Load a music track, trim to *duration* seconds, apply a *fadeout*-second
    fade-out at the tail.
    """
    audio = AudioFileClip(str(audio_path))

    # If the track is shorter than required, loop it
    if audio.duration < duration:
        loops   = int(duration / audio.duration) + 1
        from moviepy import concatenate_audioclips
        audio = concatenate_audioclips([audio] * loops)

    audio = audio.subclipped(0, duration)
    audio = AudioFadeOut(fadeout).apply(audio)

    log.info("Audio prepared: %.1fs track trimmed to %.1fs with %.1fs fade-out",
             AudioFileClip(str(audio_path)).duration, duration, fadeout)
    return audio


# ─────────────────────────────────────────────────────────────────────────────
# TEXT OVERLAY
# ─────────────────────────────────────────────────────────────────────────────

def build_text_overlay(quote: str, duration: float) -> TextClip:
    """
    Create a centred, word-wrapped TextClip for the given *quote*.
    Uses DejaVuSans-Bold (available on Arch Linux via ttf-dejavu package).
    """
    # Wrap long quotes so they stay within MAX_TEXT_WIDTH
    wrapped = textwrap.fill(quote, width=WRAP_WIDTH)
    log.info("Wrapped text:\n%s", wrapped)

    text_clip = TextClip(
        text=wrapped,
        font=FONT_PATH,
        font_size=FONT_SIZE,
        color=TEXT_COLOR,
        stroke_color=STROKE_COLOR,
        stroke_width=STROKE_WIDTH,
        method="caption",          # auto-wraps within size limit as a safety net
        size=(MAX_TEXT_WIDTH, None),
        text_align="center",
        duration=duration,
    )

    # Centre the text on the canvas
    text_clip = text_clip.with_position("center")
    return text_clip


# ─────────────────────────────────────────────────────────────────────────────
# MAIN COMPOSER
# ─────────────────────────────────────────────────────────────────────────────

def create_reel(
    output_path: Path = OUTPUT_FILE,
    duration: float   = REEL_DURATION,
) -> Path:
    """
    Orchestrate the full reel creation pipeline and return the output path.
    """
    log.info("═══ Starting Reel Generation ═══")

    # 1. Pick random assets
    bg_path    = pick_random_file(BACKGROUNDS_DIR, (".mp4", ".mov", ".avi"))
    music_path = pick_random_file(MUSIC_DIR,       (".mp3", ".wav", ".aac"))
    quote      = load_random_quote(QUOTES_FILE)

    # 2. Build individual layers
    background = prepare_background(bg_path,    duration)
    audio      = prepare_audio(music_path,      duration, AUDIO_FADEOUT)
    text       = build_text_overlay(quote,      duration)

    # 3. Composite: background + text on top
    final = CompositeVideoClip(
        [background, text],
        size=(TARGET_W, TARGET_H),
    )
    final = final.with_audio(audio)

    # 4. Export
    log.info("Rendering → %s", output_path)
    final.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",          # balance speed vs. file size
        threads=os.cpu_count(),
        logger="bar",
    )

    log.info("═══ Reel saved to %s ═══", output_path)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_reel()
