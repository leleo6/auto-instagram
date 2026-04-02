"""
instagram_uploader.py
─────────────────────────────────────────────────────────────────────────────
Modular uploader for the Instagram Graph API (Reels endpoint).

Prerequisites
─────────────────────────────────────────────────────────────────────────────
1.  A Facebook Developer App with instagram_content_publish permission.
2.  A connected Instagram *Professional* (Business or Creator) account.
3.  A long-lived User Access Token with the scopes:
       instagram_content_publish, instagram_basic

API flow (Reels, 2-step upload)
─────────────────────────────────────────────────────────────────────────────
Step 1 → POST  /v19.0/{ig_user_id}/media
            video_url=<publicly accessible URL>
            caption=<your caption>
            media_type=REELS
         → returns  { "id": "<CREATION_ID>" }

Step 2 → POST  /v19.0/{ig_user_id}/media_publish
            creation_id=<CREATION_ID>
         → returns  { "id": "<MEDIA_ID>" }  ← the published post ID

Note: The video file must be hosted at a **publicly accessible HTTPS URL**.
      Instagram cannot pull from a local path.
      You can use S3, Cloudinary, Google Cloud Storage, etc.

Replace the PLACEHOLDER values below with your real credentials before use.
"""

import os
import time
import logging
from pathlib import Path

import requests  # pip install requests

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  CREDENTIALS — replace with real values (or load from env / .env file)
# ─────────────────────────────────────────────────────────────────────────────

# Credentials are loaded from environment variables (set in .env or system env).
# main.py loads .env automatically via python-dotenv before importing this module.
ACCESS_TOKEN    = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
IG_USER_ID      = os.getenv("INSTAGRAM_USER_ID", "")
GRAPH_API_BASE  = "https://graph.facebook.com/v19.0"

# Maximum seconds to wait for Instagram to finish processing the video
PUBLISH_TIMEOUT = 120
POLL_INTERVAL   = 10   # seconds between status checks


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _raise_for_api_error(response: requests.Response) -> dict:
    """Parse the JSON response and raise a clear error on API failures."""
    data = response.json()
    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"Instagram API error {err.get('code')}: {err.get('message')}"
        )
    return data


def _poll_container_status(creation_id: str) -> None:
    """
    Wait until Instagram finishes processing the video container.
    Raises RuntimeError if it enters an error state or times out.
    """
    url    = f"{GRAPH_API_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": ACCESS_TOKEN}
    elapsed = 0

    while elapsed < PUBLISH_TIMEOUT:
        resp   = requests.get(url, params=params, timeout=30)
        data   = _raise_for_api_error(resp)
        status = data.get("status_code", "UNKNOWN")
        log.info("Container status: %s (elapsed %ds)", status, elapsed)

        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError("Instagram reported an ERROR processing the video.")

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    raise TimeoutError(
        f"Timed out waiting for Instagram to process the video "
        f"(waited {PUBLISH_TIMEOUT}s)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def upload_reel(
    public_video_url: str,
    caption: str        = "",
    access_token: str   = ACCESS_TOKEN,
    ig_user_id: str     = IG_USER_ID,
    cover_url: str      = "",   # optional thumbnail URL
) -> str:
    """
    Upload a Reel to Instagram via the Graph API.

    Parameters
    ----------
    public_video_url : str
        A publicly accessible HTTPS URL to the rendered .mp4 file.
    caption : str
        Post caption / description (supports hashtags and emojis).
    access_token : str
        Long-lived User Access Token.
    ig_user_id : str
        Numeric Instagram Business / Creator account ID.
    cover_url : str
        Optional public URL for the Reel's cover thumbnail.

    Returns
    -------
    str
        The published Instagram media ID.
    """
    log.info("Step 1/2 — Creating media container …")

    # ── Step 1: Create the media container ───────────────────────────────────
    create_payload = {
        "media_type":  "REELS",
        "video_url":   public_video_url,
        "caption":     caption,
        "access_token": access_token,
    }
    if cover_url:
        create_payload["cover_url"] = cover_url

    resp        = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data=create_payload,
        timeout=60,
    )
    data        = _raise_for_api_error(resp)
    creation_id = data["id"]
    log.info("Container created: %s", creation_id)

    # ── Wait for Instagram to process the video ───────────────────────────────
    _poll_container_status(creation_id)

    # ── Step 2: Publish the container ─────────────────────────────────────────
    log.info("Step 2/2 — Publishing container %s …", creation_id)
    publish_payload = {
        "creation_id":  creation_id,
        "access_token": access_token,
    }
    resp     = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data=publish_payload,
        timeout=30,
    )
    data     = _raise_for_api_error(resp)
    media_id = data["id"]
    log.info("✅ Reel published! Media ID: %s", media_id)
    return media_id


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST (delete in production)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Replace with a real public URL to test
    test_url = "https://your-cdn.example.com/daily_reel.mp4"
    test_cap = "✨ Daily motivation by AutoReel 🚀 #motivation #daily"

    media_id = upload_reel(
        public_video_url=test_url,
        caption=test_cap,
    )
    print(f"Published Reel ID: {media_id}")
