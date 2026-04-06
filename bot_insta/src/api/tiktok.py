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
from bot_insta.src.api.retries import with_retries
from bot_insta.src.api.base import SocialUploader
import multiprocessing

def _isolated_tiktok_upload(video_path, caption, cookies_path, proxy):
    """
    Se ejecuta en un proceso 100% aislado para evitar que Playwright
    choque con el Event Loop de Asyncio y rompa la interfaz de Tkinter al cerrarse.
    """
    from tiktok_uploader.upload import upload_video
    return upload_video(
        filename=video_path,
        description=caption,
        cookies=cookies_path,
        headless=False,
        browser="firefox",
        proxy={"server": proxy} if proxy else None
    )

log = logging.getLogger(__name__)

class TikTokUploader(SocialUploader):
    @with_retries(max_attempts=3, base_delay=15.0, exceptions=(Exception,))
    def upload(self, video_path: Path | str, caption: str, credentials: dict, proxy: str = None, abort_event=None) -> str:
        """
        Uploads a video to TikTok using browser cookies.
        Raises FileNotFoundError if cookies.txt is missing.
        Returns the string "OK" (library doesn't return canonical ID easily).
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"El video no existe: {video_path}")
            
        cookies_path_override = credentials.get("tiktok_session_id")
        cookies_path = Path(cookies_path_override) if cookies_path_override else config.get_path("tiktok_cookies")
        if not cookies_path.exists():
            log.error("Falta %s. Usa una extensión para exportar cookies de tiktok.com", cookies_path.name)
            raise FileNotFoundError(f"Falta el archivo de cookies de TikTok en: {cookies_path}")

        caption = caption or config.get("instagram", "default_caption", "✨ Daily motivation 🚀 #motivation")

        log.info("══════════════════════════════════════════")
        log.info("  TikTok Uploader")
        log.info("══════════════════════════════════════════")
        log.info("📤 Subiendo Reel a TikTok: %s", video_path.name)

        # Usamos multiprocessing para que Playwright tenga un entorno virgen
        # y no genere el error "Playwright Sync API inside asyncio loop" si se interrumpe.
        try:
            ctx = multiprocessing.get_context("spawn")
            with ctx.Pool(1) as pool:
                res = pool.apply_async(_isolated_tiktok_upload, (str(video_path), caption, str(cookies_path), proxy))
                
                # Monitoreo activo del abort_event para matar el proceso de Playwright de golpe
                while not res.ready():
                    if abort_event and abort_event.is_set():
                        log.warning("🚫 Cancelación por usuario. Matando proceso de TikTok...")
                        pool.terminate()
                        raise InterruptedError("Cancelled by user")
                    try:
                        res.wait(0.5)
                    except multiprocessing.TimeoutError:
                        pass
                
                # get() retorna la lista de videos fallidos O relanza la excepción
                # interna del proceso hijo — ambos casos quedan cubiertos.
                result = res.get()
            
            if result:
                raise RuntimeError(
                    f"La subida a TikTok falló para {len(result)} video(s). "
                    "Revisa los logs de tiktok-uploader o si el cookie expiró."
                )
            log.info("✅ Reel publicado en TikTok.")
            return "OK"
        except Exception as e:
            log.error("❌ Error subiendo a TikTok: %s", e)
            raise
