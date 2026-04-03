"""
cli.py
─────────────────────────────────────────────────────────────────────────────
Entry point for the automated daily-reel pipeline in headless mode.
Ideal for cron jobs.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Adjusting path to make sure cron triggers root correctly
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.api.instagram import upload_reel
from bot_insta.src.core.config_loader import config

# We use logging to a bot.log defined previously. Let's make sure it logs in bot_insta/logs/bot_xxx.log
LOGS_DIR = PROJECT_ROOT / "bot_insta" / "logs"
LOGS_DIR.mkdir(exist_ok=True, parents=True)
log_file = LOGS_DIR / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

def run() -> None:
    log.info("══════════════════════════════════════════")
    log.info("  Auto-Instagram Headless — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("══════════════════════════════════════════")

    try:
        reel_path = create_reel()
        log.info("✅ Reel generated: %s", reel_path)
    except Exception as exc:
        log.exception("❌ Reel generation failed: %s", exc)
        sys.exit(1)

    UPLOAD_ENABLED = os.getenv("UPLOAD", "false").lower() in ("1", "true", "yes")
    if not UPLOAD_ENABLED:
        log.info("ℹ️  Upload disabled (set UPLOAD=true in env to enable).")
        return

    try:
        media_id = upload_reel(reel_path)
        log.info("✅ Reel publicado en Instagram. Media ID: %s", media_id)
    except Exception as exc:
        log.exception("❌ Upload failed: %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    run()
