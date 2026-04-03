"""
instagram.py
─────────────────────────────────────────────────────────────────────────────
Instagram API automation using instagrapi.
Configured dynamically by the central ConfigLoader.
"""

import os
import time
import random
import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientLoginRequired
from bot_insta.src.core.config_loader import config

log = logging.getLogger(__name__)

SESSION_FILE = config.get_path("session_file")

def _build_client() -> Client:
    cl = Client()
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            log.info("📂 Sesión previa cargada desde %s", SESSION_FILE)
        except Exception as e:
            log.warning("⚠️ Error cargando sesión (%s), se pedirá nuevo login...", e)
            SESSION_FILE.unlink(missing_ok=True)
    return cl

def _login(cl: Client, username: str, password: str) -> None:
    try:
        cl.login(username, password)
        log.info("✅ Login exitoso como @%s", username)
    except Exception as exc:
        log.warning("⚠️  Login con sesión guardada falló (%s). Reintentando fresh…", exc)
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        cl = Client()
        cl.login(username, password)
        log.info("✅ Login fresh exitoso como @%s", username)
    cl.dump_settings(SESSION_FILE)
    log.info("💾 Sesión guardada en %s", SESSION_FILE)

def _human_delay(min_s: float = 2.0, max_s: float = 6.0) -> None:
    t = random.uniform(min_s, max_s)
    log.debug("⏳ Esperando %.1fs…", t)
    time.sleep(t)

def upload_reel(video_path: Path | str, caption: str = "", username: str = None, password: str = None) -> str:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"El video no existe: {video_path}")

    # Fallback to env variables if not explicitly provided
    username = username or os.getenv("INSTAGRAM_USERNAME", "")
    password = password or os.getenv("INSTAGRAM_PASSWORD", "")
    caption = caption or config.get("instagram", "default_caption", "✨ Daily motivation 🚀 #motivation")

    if not username or not password:
        raise ValueError("Missing INSTAGRAM credentials in env/parameters.")

    log.info("══════════════════════════════════════════")
    log.info("  Instagram API Uploader")
    log.info("══════════════════════════════════════════")

    cl = _build_client()
    _login(cl, username, password)
    _human_delay(3, 8)

    log.info("📤 Subiendo Reel: %s", video_path.name)
    try:
        media = cl.clip_upload(path=video_path, caption=caption)
    except (LoginRequired, ClientLoginRequired):
        log.warning("🔄 Sesión expirada. Re-autenticando…")
        SESSION_FILE.unlink(missing_ok=True)
        cl = Client()
        _login(cl, username, password)
        _human_delay(3, 6)
        media = cl.clip_upload(path=video_path, caption=caption)

    media_id = str(media.pk)
    log.info("✅ Reel publicado. Media ID: %s", media_id)
    return media_id
