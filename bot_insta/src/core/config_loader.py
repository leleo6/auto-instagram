"""
config_loader.py
─────────────────────────────────────────────────────────────────────────────
Central YAML-based configuration manager with profile CRUD support.
"""

from pathlib import Path
from dotenv import load_dotenv
from bot_insta.src.core.storage import IStorage, YamlStorage

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent  # auto-instagram/

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")

CONFIG_FILE = PROJECT_ROOT / "bot_insta" / "config" / "config.yaml"


class ConfigLoader:
    def __init__(self, config_path: Path = CONFIG_FILE, storage: IStorage = None):
        self.config_path = config_path
        self.storage = storage or YamlStorage()
        self._config = self._load()

    def _load(self) -> dict:
        data = self.storage.load(self.config_path)
        if data is None:
            raise FileNotFoundError(f"Missing config file at {self.config_path}")
            
            
        modified = False
        
        # Initialize captions block if missing
        if "captions" not in data:
            data["captions"] = {}
            modified = True

        # Migrate legacy profile captions
        for p_name, p_data in data.get("profiles", {}).items():
            if "caption" in p_data:
                legacy_str = p_data.pop("caption")
                modified = True
                
                # Try isolating hashtags from the description to create a clean new record
                parts = legacy_str.split("#", 1)
                desc = parts[0].strip()
                hashtags = ("#" + parts[1].strip()) if len(parts) > 1 else ""
                
                if p_name not in data["captions"]:
                    data["captions"][p_name] = {
                        "description": desc,
                        "hashtags": hashtags
                    }
        
        if modified:
            self.storage.save(self.config_path, data)
                
        return data

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
            return PROJECT_ROOT / prof.get("quotes_file", "bot_insta/config/quotes/quotes.txt")
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

    # ── Captions CRUD ──────────────────────────────────────────────────────────
    def list_captions(self) -> list[str]:
        return list(self._config.get("captions", {}).keys())

    def get_caption_data(self, name: str) -> dict:
        return self._config.get("captions", {}).get(name, {"description": "", "hashtags": ""})

    def update_caption(self, name: str, description: str, hashtags: str) -> None:
        captions = self._config.setdefault("captions", {})
        captions[name] = {"description": description, "hashtags": hashtags}
        self.save()

    def delete_caption(self, name: str) -> None:
        captions = self._config.get("captions", {})
        if name in captions:
            del captions[name]
            self.save()

    # ── Quotes CRUD (File-based) ───────────────────────────────────────────────
    def get_quotes_dir(self) -> Path:
        d = PROJECT_ROOT / "bot_insta" / "config" / "quotes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def list_quote_groups(self) -> list[str]:
        d = self.get_quotes_dir()
        return sorted([f.stem for f in d.glob("*.txt")])

    def get_quote_file(self, name: str) -> Path:
        return self.get_quotes_dir() / f"{name}.txt"

    def read_quote_group(self, name: str) -> str:
        f = self.get_quote_file(name)
        return f.read_text("utf-8") if f.exists() else ""

    def save_quote_group(self, name: str, content: str) -> None:
        if not name: return
        self.get_quote_file(name).write_text(content, "utf-8")

    def delete_quote_group(self, name: str) -> None:
        f = self.get_quote_file(name)
        if f.exists(): f.unlink()

    # ── Persistence ────────────────────────────────────────────────────────────
    def save(self) -> None:
        self.storage.save(self.config_path, self._config)

    def reload(self) -> None:
        self._config = self._load()


# Singleton
config = ConfigLoader()
