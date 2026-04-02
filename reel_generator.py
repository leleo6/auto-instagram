"""
reel_generator.py
─────────────────────────────────────────────────────────────────────────────
Genera un Reel diario 9:16 combinando:
  - Un video de fondo aleatorio  (./backgrounds/*.mp4)
  - Una pista de música aleatoria (./music/*.mp3)
  - Una frase aleatoria           (./quotes.txt)

Estilo de texto: serif itálica elegante, blanco puro, sin borde,
                 con comillas tipográficas — igual a la referencia visual.

Output: output/reel_YYYY-MM-DD.mp4  (1080 x 1920, 10 segundos)

Dependencias:
  pip install "moviepy==1.0.3" Pillow
  (moviepy 1.0.3 requerido por instagrapi)
"""

import os
import random
import textwrap
import logging
from pathlib import Path

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    concatenate_audioclips,
)
from moviepy.audio.fx.audio_fadeout import audio_fadeout

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

TARGET_W      = 1080
TARGET_H      = 1920
REEL_DURATION = 10          # segundos
AUDIO_FADEOUT = 2           # segundos de fade-out al final

# Rutas absolutas → funciona correctamente con cron
_HERE           = Path(__file__).resolve().parent
BACKGROUNDS_DIR = _HERE / "backgrounds"
MUSIC_DIR       = _HERE / "music"
QUOTES_FILE     = _HERE / "quotes.txt"
OUTPUT_FILE     = _HERE / "output" / "reel_del_dia.mp4"

# ── Estilo de texto: serif itálica, blanco, sin borde, comillas tipográficas ──
FONT_PATH      = "/usr/share/fonts/gnu-free/FreeSerifItalic.otf"
FONT_SIZE      = 72
TEXT_COLOR     = "white"
STROKE_WIDTH   = 0           # sin borde
MAX_TEXT_WIDTH = 880         # píxeles
WRAP_WIDTH     = 30          # caracteres por línea

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ASSET HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def pick_random_file(directory: Path, extensions: tuple) -> Path:
    """Devuelve un archivo aleatorio con alguna de las extensiones dadas."""
    files = [f for f in directory.iterdir() if f.suffix.lower() in extensions]
    if not files:
        raise FileNotFoundError(
            f"No hay archivos con extensiones {extensions} en '{directory}'."
        )
    chosen = random.choice(files)
    log.info("Seleccionado: %s", chosen.name)
    return chosen


def load_random_quote(quotes_file: Path) -> str:
    """Lee quotes.txt y devuelve una línea aleatoria no vacía."""
    with quotes_file.open("r", encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        raise ValueError(f"'{quotes_file}' está vacío.")
    quote = random.choice(lines)
    log.info("Frase seleccionada: %r", quote)
    return quote


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def prepare_background(video_path: Path, duration: float) -> VideoFileClip:
    """
    Carga el video de fondo, lo repite si es necesario, lo recorta a
    *duration* segundos y lo escala/cropea a 1080×1920 (cover strategy).
    """
    clip = VideoFileClip(str(video_path))

    # Repetir si el clip es más corto que la duración deseada
    if clip.duration < duration:
        loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)

    clip = clip.subclip(0, duration)

    # Escalar para cubrir el frame completo (cover), luego center-crop
    clip_ratio   = clip.w / clip.h
    target_ratio = TARGET_W / TARGET_H

    if clip_ratio > target_ratio:
        new_h = TARGET_H
        new_w = int(clip.w * TARGET_H / clip.h)
    else:
        new_w = TARGET_W
        new_h = int(clip.h * TARGET_W / clip.w)

    resized = clip.resize((new_w, new_h))

    x1 = (new_w - TARGET_W) // 2
    y1 = (new_h - TARGET_H) // 2
    cropped = resized.crop(x1=x1, y1=y1, x2=x1 + TARGET_W, y2=y1 + TARGET_H)

    log.info("Fondo: %dx%d → %dx%d", clip.w, clip.h, TARGET_W, TARGET_H)
    return cropped


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def prepare_audio(audio_path: Path, duration: float, fadeout: float) -> AudioFileClip:
    """
    Carga la pista, la repite si es necesario, la recorta a *duration*
    segundos y aplica un fade-out al final.
    """
    audio = AudioFileClip(str(audio_path))

    if audio.duration < duration:
        loops = int(duration / audio.duration) + 1
        audio = concatenate_audioclips([audio] * loops)

    audio = audio.subclip(0, duration)
    audio = audio_fadeout(audio, fadeout)

    log.info("Audio preparado: %.1fs → %.1fs con %.1fs fade-out",
             AudioFileClip(str(audio_path)).duration, duration, fadeout)
    return audio


# ─────────────────────────────────────────────────────────────────────────────
# TEXT OVERLAY
# ─────────────────────────────────────────────────────────────────────────────

def build_text_overlay(quote: str, duration: float) -> TextClip:
    """
    Crea un TextClip centrado con la frase entre comillas tipográficas.
    Estilo: serif itálica elegante, blanco puro, sin borde.
    """
    # Comillas tipográficas curvas
    quoted  = f"\u201c{quote}\u201d"
    wrapped = textwrap.fill(quoted, width=WRAP_WIDTH)
    log.info("Texto formateado:\n%s", wrapped)

    text_clip = TextClip(
        wrapped,
        fontsize=FONT_SIZE,
        font=FONT_PATH,
        color=TEXT_COLOR,
        stroke_width=STROKE_WIDTH,
        method="caption",
        size=(MAX_TEXT_WIDTH, None),
        align="center",
    ).set_duration(duration).set_position("center")

    return text_clip


# ─────────────────────────────────────────────────────────────────────────────
# MAIN COMPOSER
# ─────────────────────────────────────────────────────────────────────────────

def create_reel(
    output_path: Path = OUTPUT_FILE,
    duration: float   = REEL_DURATION,
) -> Path:
    """Orquesta el pipeline completo y devuelve la ruta del video generado."""
    log.info("═══ Iniciando generación del Reel ═══")

    bg_path    = pick_random_file(BACKGROUNDS_DIR, (".mp4", ".mov", ".avi"))
    music_path = pick_random_file(MUSIC_DIR,       (".mp3", ".wav", ".aac"))
    quote      = load_random_quote(QUOTES_FILE)

    background = prepare_background(bg_path, duration)
    audio      = prepare_audio(music_path, duration, AUDIO_FADEOUT)
    text       = build_text_overlay(quote, duration)

    final = CompositeVideoClip(
        [background, text],
        size=(TARGET_W, TARGET_H),
    ).set_audio(audio)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("Renderizando → %s", output_path)
    final.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=os.cpu_count(),
        logger="bar",
    )

    log.info("═══ Reel guardado en %s ═══", output_path)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_reel()
