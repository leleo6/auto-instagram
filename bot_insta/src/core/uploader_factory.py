from bot_insta.src.api.base import SocialUploader
from bot_insta.src.api.instagram import InstagramUploader
from bot_insta.src.api.tiktok import TikTokUploader
from bot_insta.src.api.youtube import YouTubeUploader

class UploaderFactory:
    _uploaders = {
        "Instagram": InstagramUploader,
        "TikTok": TikTokUploader,
        "YouTube": YouTubeUploader
    }

    @classmethod
    def get_uploader(cls, platform: str) -> SocialUploader:
        uploader_class = cls._uploaders.get(platform)
        if not uploader_class:
            raise ValueError(f"Platform '{platform}' is not supported.")
        return uploader_class()
