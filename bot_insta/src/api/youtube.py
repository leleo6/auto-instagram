"""
youtube.py
─────────────────────────────────────────────────────────────────────────────
YouTube Data API v3 automation using google-api-python-client.
Requires a client_secrets.json from GCP.
"""

import logging
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from bot_insta.src.core.config_loader import config

log = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_youtube_service(client_secrets_override: str = None, token_override: str = None):
    """Authenticates using client_secrets and returns a YouTube resource."""
    creds = None
    token_path = Path(token_override) if token_override else config.get_path("youtube_token")
    client_secrets_path = Path(client_secrets_override) if client_secrets_override else config.get_path("youtube_client_secrets")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("🔄 Refrescando token de YouTube...")
            creds.refresh(Request())
        else:
            if not client_secrets_path.exists():
                raise FileNotFoundError(
                    f"Falta {client_secrets_path.name}. Descárgalo desde Google Cloud Console."
                )
            log.info("🌐 Abriendo navegador para autorización de YouTube...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)


def upload_youtube(video_path: Path | str, caption: str = "", privacy: str = "unlisted", client_secrets_override: str = None, token_override: str = None) -> str:
    """
    Subida usando la API de YouTube. Se recomienda enviar videos #Shorts (verticales, <60s).
    Retorna el VideoId de YouTube.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"El video no existe: {video_path}")

    caption = caption or config.get("instagram", "default_caption", "✨ Daily motivation 🚀 #motivation")
    # For YouTube shorts, titles are usually extracted from the first line or are shorter
    title = caption.split('\n')[0][:95] if caption else f"Auto Upload {video_path.stem}"
    if "#shorts" not in caption.lower():
        caption += "\n#shorts"

    log.info("══════════════════════════════════════════")
    log.info("  YouTube (Shorts) API Uploader")
    log.info("══════════════════════════════════════════")

    youtube = get_youtube_service(client_secrets_override, token_override)

    body = {
        'snippet': {
            'title': title,
            'description': caption,
            'categoryId': '22'  # People & Blogs
        },
        'status': {
            'privacyStatus': privacy.lower(),
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(str(video_path), mimetype='video/mp4', resumable=True)

    log.info("📤 Subiendo a YouTube (%s): %s", privacy, video_path.name)
    
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = request.execute()
    vid_id = response.get('id')
    log.info("✅ YouTube upload OK. Video ID: %s", vid_id)
    return vid_id
