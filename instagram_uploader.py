"""
instagram_uploader.py
─────────────────────────────────────────────────────────────────────────────
Sube un Reel a Instagram usando instagrapi (API privada).

Características anti-bot:
  - Sesión persistente en session.json → evita login en cada ejecución.
  - Simula un dispositivo Android real (mismo UUID entre sesiones).
  - Delays aleatorios entre acciones.
  - Re-login automático si la sesión expira.

Variables de entorno requeridas (.env):
  INSTAGRAM_USERNAME  → tu @usuario (sin @)
  INSTAGRAM_PASSWORD  → tu contraseña
"""

import os
import time
import random
import logging
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientLoginRequired

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

_HERE        = Path(__file__).resolve().parent
SESSION_FILE = _HERE / "session.json"


def _build_client() -> Client:
    """
    Crea un Client con configuración de dispositivo consistente.
    Si ya existe session.json se carga el UUID/device guardado para que
    Instagram reconozca el mismo "teléfono" entre sesiones.
    """
    cl = Client()

    # Cargar configuración previa (device UUID, cookies, tokens…)
    if SESSION_FILE.exists():
        cl.load_settings(SESSION_FILE)
        log.info("📂 Sesión previa cargada desde %s", SESSION_FILE)

    return cl


def _login(cl: Client, username: str, password: str) -> None:
    """
    Inicia sesión. Si la sesión guardada sigue siendo válida, solo
    refresca las cookies (mucho más rápido y menos detectable).
    """
    try:
        cl.login(username, password)
        log.info("✅ Login exitoso como @%s", username)
    except Exception as exc:
        log.warning("⚠️  Login con sesión guardada falló (%s). Reintentando fresh…", exc)
        # Borrar sesión rota y reintentar desde cero
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        cl = Client()          # cliente limpio sin settings anteriores
        cl.login(username, password)
        log.info("✅ Login fresh exitoso como @%s", username)

    # Siempre persistir la sesión actualizada
    cl.dump_settings(SESSION_FILE)
    log.info("💾 Sesión guardada en %s", SESSION_FILE)


def _human_delay(min_s: float = 2.0, max_s: float = 6.0) -> None:
    """Espera aleatoria para simular comportamiento humano."""
    t = random.uniform(min_s, max_s)
    log.debug("⏳ Esperando %.1fs…", t)
    time.sleep(t)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def upload_reel(
    video_path: Path | str,
    caption: str = "",
    username: str | None = None,
    password: str | None = None,
) -> str:
    """
    Sube el video local a Instagram como Reel.

    Parameters
    ----------
    video_path : Path | str
        Ruta local al archivo .mp4 (1080x1920).
    caption : str
        Pie de foto / descripción del Reel (hashtags y emojis incluidos).
    username : str | None
        @usuario. Si es None, se lee de INSTAGRAM_USERNAME.
    password : str | None
        Contraseña. Si es None, se lee de INSTAGRAM_PASSWORD.

    Returns
    -------
    str
        El media_pk (ID) del Reel publicado.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"El video no existe: {video_path}")

    username = username or os.getenv("INSTAGRAM_USERNAME", "")
    password = password or os.getenv("INSTAGRAM_PASSWORD", "")

    if not username or not password:
        raise ValueError(
            "Faltan credenciales. Define INSTAGRAM_USERNAME e "
            "INSTAGRAM_PASSWORD en tu archivo .env"
        )

    log.info("══════════════════════════════════════════")
    log.info("  Instagram Uploader  (instagrapi)")
    log.info("══════════════════════════════════════════")

    # ── 1. Construir cliente con sesión previa ────────────────────────────────
    cl = _build_client()

    # ── 2. Login (reutiliza cookies si son válidas) ───────────────────────────
    _login(cl, username, password)

    # ── 3. Pequeña pausa antes de subir ──────────────────────────────────────
    _human_delay(3, 8)

    # ── 4. Subir el Reel ─────────────────────────────────────────────────────
    log.info("📤 Subiendo Reel: %s", video_path.name)
    try:
        media = cl.clip_upload(
            path=video_path,
            caption=caption,
        )
    except (LoginRequired, ClientLoginRequired):
        # Sesión expirada durante el upload → re-login y reintentar
        log.warning("🔄 Sesión expirada. Re-autenticando…")
        SESSION_FILE.unlink(missing_ok=True)
        cl = Client()
        _login(cl, username, password)
        _human_delay(3, 6)
        media = cl.clip_upload(path=video_path, caption=caption)

    media_id = str(media.pk)
    log.info("✅ Reel publicado. Media ID: %s", media_id)
    return media_id
