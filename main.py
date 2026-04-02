"""
main.py
─────────────────────────────────────────────────────────────────────────────
Entry point for the automated daily-reel pipeline.

  1. Generates the reel via reel_generator.py
  2. (Optional) Uploads it to Instagram via instagram_uploader.py

Designed to be called by cron with absolute paths — cron does not have the
same $PATH or working directory as your shell session.

Usage
─────
  # Run manually from the project root:
  python main.py

  # Cron example (runs daily at 09:00 local time):
  0 9 * * * /home/leo/Documents/proyects/auto-instagram/.venv/bin/python \
            /home/leo/Documents/proyects/auto-instagram/main.py \
            >> /home/leo/Documents/proyects/auto-instagram/logs/cron.log 2>&1
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# ── Make sure cron can find the project modules regardless of CWD ────────────
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)          # set CWD so relative paths in sub-modules work
sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env file if python-dotenv is available (optional dependency) ───────
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed — rely on environment variables directly

# ── Logging: file + console ───────────────────────────────────────────────────
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

log_file = LOGS_DIR / f"reel_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Project imports (after CWD & sys.path are set) ───────────────────────────
from reel_generator import create_reel          # noqa: E402
from instagram_uploader import upload_reel      # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION (overridable via environment variables)
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR       = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Name the file with today's date so old reels are kept and not overwritten
OUTPUT_FILE      = OUTPUT_DIR / f"reel_{datetime.now().strftime('%Y-%m-%d')}.mp4"

# Set UPLOAD=true in the environment (or .env) to enable the Instagram upload
UPLOAD_ENABLED   = os.getenv("UPLOAD", "false").lower() in ("1", "true", "yes")

REEL_CAPTION = os.getenv(
    "REEL_CAPTION",
    "✨ Daily motivation 🚀 #motivation #mindset #daily",
)


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    log.info("══════════════════════════════════════════")
    log.info("  Auto-Instagram  —  %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("══════════════════════════════════════════")

    # ── Step 1: Generate the reel ─────────────────────────────────────────────
    try:
        reel_path = create_reel(output_path=OUTPUT_FILE)
        log.info("✅ Reel generated: %s", reel_path)
    except Exception as exc:
        log.exception("❌ Reel generation failed: %s", exc)
        sys.exit(1)

    # ── Step 2: Upload to Instagram (optional) ────────────────────────────────
    if not UPLOAD_ENABLED:
        log.info("ℹ️  Upload disabled (set UPLOAD=true to enable).")
        log.info("   Local file: %s", reel_path)
        return

    try:
        media_id = upload_reel(
            video_path=reel_path,
            caption=REEL_CAPTION,
        )
        log.info("✅ Reel publicado en Instagram. Media ID: %s", media_id)
    except Exception as exc:
        log.exception("❌ Upload failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    run()
