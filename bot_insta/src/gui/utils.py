import PIL.Image, PIL.ImageDraw
import customtkinter as ctk
from bot_insta.src.core.video_engine import VideoContext

def create_platform_icon(platform: str) -> ctk.CTkImage:
    img = PIL.Image.new("RGBA", (24, 24), (0,0,0,0))
    d = PIL.ImageDraw.Draw(img)
    if platform == "Instagram":
        d.rounded_rectangle([3, 3, 21, 21], radius=6, outline="#E1306C", width=2)
        d.ellipse([8, 8, 16, 16], outline="#E1306C", width=2)
        d.ellipse([17, 5, 19, 7], fill="#E1306C")
    elif platform == "TikTok":
        d.line([14, 18, 14, 8], fill="#25F4EE", width=2)
        d.line([14, 8, 18, 8], fill="#FE2C55", width=2)
        d.ellipse([8, 14, 14, 20], fill="#25F4EE")
    elif platform == "YouTube":
        d.rounded_rectangle([3, 7, 21, 17], radius=3, fill="#FF0000")
        d.polygon([(10, 9), (10, 15), (15, 12)], fill="white")
    else:
        d.ellipse([4, 4, 20, 20], outline="#aaaaaa", width=2)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))

def make_video_context(config, profile: str, quotes_file_override=None) -> VideoContext:
    """Construye un VideoContext para el perfil dado SIN mutar el estado global de config.
    
    BUG-03 fix: leer datos del perfil directamente en vez de cambiar active_profile,
    lo que era una race condition cuando había múltiples jobs corriendo en paralelo.
    """
    # Leer datos directamente del perfil solicitado (thread-safe, sin mutar el singleton)
    prof_data = config._config.get("profiles", {}).get(profile, {})
    vid_cfg   = config.get_video_settings()

    from bot_insta.src.core.config_loader import PROJECT_ROOT

    # ── Background Path ───────────────────────────────────────────────────────
    base_bg   = PROJECT_ROOT / config._config["paths"]["base_backgrounds"]
    sub_bg    = prof_data.get("backgrounds_subfolder", "")
    bg_dir    = base_bg / sub_bg if sub_bg else base_bg

    # ── Music Path ────────────────────────────────────────────────────────────
    base_mu   = PROJECT_ROOT / config._config["paths"]["base_music"]
    sub_mu    = prof_data.get("music_subfolder", "")
    music_dir = base_mu / sub_mu if sub_mu else base_mu

    if quotes_file_override:
        quotes_file = quotes_file_override
    else:
        quotes_file = PROJECT_ROOT / prof_data.get(
            "quotes_file", "bot_insta/config/quotes/quotes.txt"
        )

    output_dir = config.get_path("output_dir")

    target_w  = vid_cfg.get("target_w", 1080)
    target_h  = vid_cfg.get("target_h", 1920)
    fadeout   = vid_cfg.get("audio_fadeout", 2)

    text_cfg  = prof_data.get("text",  {})
    audio_cfg = prof_data.get("audio", {})
    volume    = float(audio_cfg.get("volume", 1.0))

    duration  = prof_data.get("duration", vid_cfg.get("duration", 10))
    overlay_name = prof_data.get("overlay_image", "")
    overlay_path = config.get_path("overlays") / overlay_name if overlay_name else None

    return VideoContext(
        bg_dir=bg_dir, music_dir=music_dir, quotes_file=quotes_file, output_dir=output_dir,
        target_w=target_w, target_h=target_h, fadeout=fadeout, volume=volume, duration=duration,
        text_cfg=text_cfg, overlay_path=overlay_path
    )
