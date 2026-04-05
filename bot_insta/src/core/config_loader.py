"""
config_loader.py
─────────────────────────────────────────────────────────────────────────────
Central YAML-based configuration manager with profile CRUD support.
"""

import yaml
from pathlib import Path
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent  # auto-instagram/

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")

CONFIG_FILE = PROJECT_ROOT / "bot_insta" / "config" / "config.yaml"


class ConfigLoader:
    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self._config = self._load()

    def _load(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Missing config file at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ── Path resolution ────────────────────────────────────────────────────────
    def get_path(self, key: str) -> Path:
        # First resolve well-known logical keys
        if key in ("output_dir", "session_file"):
            return PROJECT_ROOT / self._config["paths"][key]

        active_prof = self.get_active_profile()
        prof = self._config.get("profiles", {}).get(active_prof, {})

        if key == "backgrounds":
            base = PROJECT_ROOT / self._config["paths"]["base_backgrounds"]
            sub = prof.get("backgrounds_subfolder", "")
            return base / sub if sub else base
        if key == "music":
            base = PROJECT_ROOT / self._config["paths"]["base_music"]
            sub = prof.get("music_subfolder", "")
            return base / sub if sub else base
        if key == "quotes":
            return PROJECT_ROOT / prof.get("quotes_file", "bot_insta/config/quotes.txt")
        if key == "overlays":
            return PROJECT_ROOT / self._config["paths"].get("base_overlays", "bot_insta/assets/overlays")

        # Generic fallback: any key present in the global `paths` block
        paths = self._config.get("paths", {})
        if key in paths:
            return PROJECT_ROOT / paths[key]

        raise KeyError(f"Path key '{key}' not found.")

    # ── Active profile helpers ─────────────────────────────────────────────────
    def get_active_profile(self) -> str:
        return self._config.get("active_profile", "default")

    def get_active_profile_data(self) -> dict:
        name = self.get_active_profile()
        return self._config.get("profiles", {}).get(name, {})

    def get_video_settings(self) -> dict:
        return self._config.get("video", {})

    def get_text_settings(self) -> dict:
        return self.get_active_profile_data().get("text", {})

    def get_audio_settings(self) -> dict:
        return self.get_active_profile_data().get("audio", {})

    def get(self, section: str, key: str | None = None, default=None):
        sec = self._config.get(section, {})
        if key:
            return sec.get(key, default)
        return sec

    # ── Profile CRUD ───────────────────────────────────────────────────────────
    def list_profiles(self) -> list[str]:
        return list(self._config.get("profiles", {}).keys())

    def create_profile(self, name: str, source_profile: str = "default") -> None:
        """Clone an existing profile under a new name."""
        import copy
        profiles = self._config.setdefault("profiles", {})
        if name in profiles:
            raise ValueError(f"Profile '{name}' already exists.")
        source = profiles.get(source_profile, {})
        profiles[name] = copy.deepcopy(source)
        self.save()

    def delete_profile(self, name: str) -> None:
        """Remove a profile. Cannot delete the active profile."""
        if name == self.get_active_profile():
            raise ValueError("Cannot delete the active profile.")
        profiles = self._config.get("profiles", {})
        if name not in profiles:
            raise KeyError(f"Profile '{name}' not found.")
        del profiles[name]
        self.save()

    def set_active_profile(self, name: str) -> None:
        if name not in self._config.get("profiles", {}):
            raise KeyError(f"Profile '{name}' not found.")
        self._config["active_profile"] = name
        self.save()

    # ── Persistence ────────────────────────────────────────────────────────────
    def save(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def reload(self) -> None:
        self._config = self._load()


# Singleton
config = ConfigLoader()
