"""
tiktok.py
─────────────────────────────────────────────────────────────────────────────
TikTok API automation using the unofficial `tiktok-uploader` (Playwright).
Requires a valid cookies.txt file in the config folder.
"""

import logging
from pathlib import Path

from bot_insta.src.core.config_loader import config
from tiktok_uploader.upload import upload_video

log = logging.getLogger(__name__)

def upload_tiktok(video_path: Path | str, caption: str = "", cookies_path_override: Path | str = None) -> str:
    """
    Uploads a video to TikTok using browser cookies.
    Raises FileNotFoundError if cookies.txt is missing.
    Returns the string "OK" (library doesn't return canonical ID easily).
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"El video no existe: {video_path}")

    cookies_path = Path(cookies_path_override) if cookies_path_override else config.get_path("tiktok_cookies")
    if not cookies_path.exists():
        log.error("Falta %s. Usa una extensión para exportar cookies de tiktok.com", cookies_path.name)
        raise FileNotFoundError(f"Falta el archivo de cookies de TikTok en: {cookies_path}")

    caption = caption or config.get("instagram", "default_caption", "✨ Daily motivation 🚀 #motivation")

    log.info("══════════════════════════════════════════")
    log.info("  TikTok Uploader")
    log.info("══════════════════════════════════════════")
    log.info("📤 Subiendo Reel a TikTok: %s", video_path.name)

    # Note: Headless=True by default. Can fail if TikTok prompts captcha.
    try:
        failed = upload_video(
            filename=str(video_path),
            description=caption,
            cookies=str(cookies_path),
            headless=True
        )
        if failed:
            raise RuntimeError("La subida a TikTok falló. Revisa logs de tiktok-uploader o si el cookie expiró.")
        log.info("✅ Reel publicado en TikTok.")
        return "OK"
    except Exception as e:
        log.error("❌ Error subiendo a TikTok: %s", e)
        raise
