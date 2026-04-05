from abc import ABC, abstractmethod
from pathlib import Path

class SocialUploader(ABC):
    @abstractmethod
    def upload(self, video_path: Path, caption: str, credentials: dict, proxy: str = None, abort_event=None) -> str:
        """
        Uploads a video to the specific social media platform.
        :param video_path: Path to the video file.
        :param caption: The caption/description for the video.
        :param credentials: A dictionary containing the credentials needed for the platform.
        :param proxy: Optional proxy setting.
        :return: A string identifier (Media ID, Post ID, etc) upon success.
        """
        pass
