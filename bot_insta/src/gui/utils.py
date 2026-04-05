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

def make_video_context(config, profile) -> VideoContext:
    orig = config.get_active_profile()
    config._config["active_profile"] = profile
    bg_dir      = config.get_path("backgrounds")
    music_dir   = config.get_path("music")
    quotes_file = config.get_path("quotes")
    output_dir  = config.get_path("output_dir")

    vid_cfg   = config.get_video_settings()
    target_w  = vid_cfg.get("target_w", 1080)
    target_h  = vid_cfg.get("target_h", 1920)
    fadeout   = vid_cfg.get("audio_fadeout", 2)

    text_cfg  = config.get_text_settings()
    audio_cfg = config.get_audio_settings()
    volume    = float(audio_cfg.get("volume", 1.0))

    prof_data = config.get_active_profile_data()
    duration  = prof_data.get("duration", vid_cfg.get("duration", 10))
    overlay_name = prof_data.get("overlay_image", "")
    overlay_path = config.get_path("overlays") / overlay_name if overlay_name else None
    
    config._config["active_profile"] = orig
    
    return VideoContext(
        bg_dir=bg_dir, music_dir=music_dir, quotes_file=quotes_file, output_dir=output_dir,
        target_w=target_w, target_h=target_h, fadeout=fadeout, volume=volume, duration=duration,
        text_cfg=text_cfg, overlay_path=overlay_path
    )
