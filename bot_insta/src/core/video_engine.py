"""
video_engine.py
─────────────────────────────────────────────────────────────────────────────
Genera un Reel diario 9:16 combinando videos, audios y texto.
Soporta: fade-in de texto, volumen de audio, e imagen overlay opcional.
"""

import os
import random
import textwrap
import logging
import datetime
from pathlib import Path
from dataclasses import dataclass

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', PIL.Image.Resampling.LANCZOS)

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    concatenate_audioclips,
)
import moviepy.video.fx.all as vfx
from moviepy.audio.fx.audio_fadeout import audio_fadeout
from proglog import ProgressBarLogger

@dataclass
class VideoContext:
    bg_dir: Path
    music_dir: Path
    quotes_file: Path
    output_dir: Path
    target_w: int = 1080
    target_h: int = 1920
    fadeout: float = 2.0
    volume: float = 1.0
    duration: float = 10.0
    text_cfg: dict = None
    overlay_path: Path = None

log = logging.getLogger(__name__)

class GUILogger(ProgressBarLogger):
    def __init__(self, on_progress=None, abort_event=None):
        super().__init__()
        self.on_progress = on_progress
        self.abort_event = abort_event
        self.bar_totals = {}

    def callback(self, **kw):
        # Moviepy calls this for text messages (e.g., logger(message="..."))
        # We can safely ignore it to avoid UI disruption.
        pass

    def bars_callback(self, bar, attr, value, old_value=None):
        if self.abort_event and self.abort_event.is_set():
            raise InterruptedError("Render cancelled by user")
        
        if attr == 'total':
            self.bar_totals[bar] = value
        elif attr == 'index':
            total = self.bar_totals.get(bar, 100)
            if total > 0 and self.on_progress:
                # Limit callback granularity to avoid flooding tkinter
                self.on_progress(min(1.0, value / total))


def pick_random_file(directory: Path, extensions: tuple) -> Path:
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directorio de recursos no existe: {directory}")
    files = [f for f in directory.iterdir() if f.suffix.lower() in extensions]
    if not files:
        raise FileNotFoundError(f"No hay archivos {extensions} en '{directory}'.")
    chosen = random.choice(files)
    log.info("Seleccionado asset: %s", chosen.name)
    return chosen


def load_random_quote(quotes_file: Path) -> str:
    if not quotes_file.exists():
        raise FileNotFoundError(f"Quotes file not found: {quotes_file}")
    with quotes_file.open("r", encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    if not lines:
        raise ValueError(f"'{quotes_file}' está vacío.")
    quote = random.choice(lines)
    log.info("Frase seleccionada: %r", quote)
    return quote


def prepare_background(video_path: Path, duration: float, target_w: int, target_h: int) -> VideoFileClip:
    # EC-09 fix: dimensiones inválidas causan ZeroDivisionError en el cálculo de ratio
    if target_w <= 0 or target_h <= 0:
        raise ValueError(f"Dimensiones de video inválidas: {target_w}x{target_h}")
    clip = VideoFileClip(str(video_path), audio=False)
    if clip.duration < duration:
        clip = clip.fx(vfx.loop, duration=duration)
    else:
        clip = clip.subclip(0, duration)

    clip_ratio   = clip.w / clip.h
    target_ratio = target_w / target_h

    if clip_ratio > target_ratio:
        new_h = target_h
        new_w = int(clip.w * target_h / clip.h)
    else:
        new_w = target_w
        new_h = int(clip.h * target_w / clip.w)

    resized = clip.resize((new_w, new_h))
    x1 = (new_w - target_w) // 2
    y1 = (new_h - target_h) // 2
    return resized.crop(x1=x1, y1=y1, x2=x1 + target_w, y2=y1 + target_h)


def prepare_audio(audio_path: Path, duration: float, fadeout: float, volume: float = 1.0) -> AudioFileClip:
    audio = AudioFileClip(str(audio_path))
    # EC-01 fix: archivo de audio vacío o inválido causa ZeroDivisionError
    if audio.duration <= 0:
        audio.close()
        raise ValueError(
            f"El archivo de audio '{audio_path.name}' tiene duración cero o es inválido."
        )
    if audio.duration < duration:
        loops = int(duration / audio.duration) + 1
        audio = concatenate_audioclips([audio] * loops)
    audio = audio.subclip(0, duration)
    if volume != 1.0:
        audio = audio.volumex(max(0.0, min(1.0, volume)))
    return audio_fadeout(audio, fadeout)


def build_text_overlay(quote: str, duration: float, text_cfg: dict) -> TextClip:
    wrapped = textwrap.fill(quote, width=text_cfg.get('wrap_width', 30))

    # Position
    raw_pos = text_cfg.get("position", "center")
    if isinstance(raw_pos, list) and len(raw_pos) == 2:
        pos = (raw_pos[0], raw_pos[1])
    else:
        pos = raw_pos

    kwargs = {
        "fontsize": text_cfg.get('font_size', 72),
        "font": text_cfg.get('font_path', 'Arial'),
        "color": str(text_cfg.get('color', 'white')),
        "method": "caption",
        "size": (text_cfg.get('max_width', 880), None),
        "align": "center",
    }
    stroke = text_cfg.get('stroke_width', 0)
    if stroke > 0:
        kwargs["stroke_width"] = stroke
        kwargs["stroke_color"] = text_cfg.get('stroke_color', 'black')

    clip = TextClip(wrapped, **kwargs).set_duration(duration).set_position(pos)

    # Fade-in animation
    fadein_s = float(text_cfg.get('fadein', 0))
    if fadein_s > 0:
        clip = clip.crossfadein(fadein_s)

    return clip


def build_overlay(overlay_path: Path, duration: float, target_w: int, target_h: int):
    """Load a PNG watermark/logo and place it bottom-right with 80% opacity."""
    if not overlay_path or not overlay_path.exists():
        return None
    img = ImageClip(str(overlay_path), ismask=False)
    # Scale to ~15% of frame width
    scale = (target_w * 0.15) / img.w
    img = img.resize(scale)
    # Position: 20px from bottom-right
    x = target_w - img.w - 20
    y = target_h - img.h - 20
    return img.set_position((x, y)).set_duration(duration).set_opacity(0.8)


def create_reel(context: VideoContext, progress_callback=None, abort_event=None) -> Path:
    """Full pipeline orchestrator — reads active profile from context."""
    log.info("═══ Iniciando generación del Reel ═══")

    text_cfg  = context.text_cfg or {}

    # ── Pick assets ─────────────────────────────────────────────────────────────
    bg_path    = pick_random_file(context.bg_dir,    (".mp4", ".mov", ".avi"))
    music_path = pick_random_file(context.music_dir, (".mp3", ".wav", ".aac"))
    quote      = load_random_quote(context.quotes_file)

    # ── Build clips ─────────────────────────────────────────────────────────────
    background = prepare_background(bg_path, context.duration, context.target_w, context.target_h)
    audio      = prepare_audio(music_path, context.duration, context.fadeout, context.volume)
    text       = build_text_overlay(quote, context.duration, text_cfg)

    try:
        layers = [background, text]

        # Optional overlay/watermark
        overlay_clip = None
        if context.overlay_path:
            overlay_clip = build_overlay(context.overlay_path, context.duration, context.target_w, context.target_h)
            if overlay_clip:
                layers.append(overlay_clip)

        final = CompositeVideoClip(layers, size=(context.target_w, context.target_h)).set_audio(audio)

        # ── Export ─────────────────────────────────────────────────────────────
        import uuid
        today    = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        context.output_dir.mkdir(parents=True, exist_ok=True)
        out_file = context.output_dir / f"reel_{today}_{short_id}.mp4"

        log.info("Renderizando → %s", out_file)
        logger_obj = GUILogger(on_progress=progress_callback, abort_event=abort_event)

        final.write_videofile(
            str(out_file),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=os.cpu_count(),
            logger=logger_obj,
        )
        log.info("═══ Reel guardado en %s ═══", out_file)
        return out_file

    finally:
        # BUG-06 fix: liberar file descriptors de MoviePy sea cual sea el resultado.
        # overlay_clip siempre está definido (como None) antes del try, por lo que
        # filter(None, ...) simplemente lo omite si no fue creado.
        for clip in filter(None, [background, audio, text, overlay_clip]):
            try:
                clip.close()
            except Exception:
                pass
