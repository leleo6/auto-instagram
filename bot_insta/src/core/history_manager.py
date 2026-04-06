import json
import logging
from pathlib import Path
from datetime import datetime

from bot_insta.src.core.config_loader import PROJECT_ROOT

log = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, history_file: Path = None):
        self.history_file = history_file or (PROJECT_ROOT / "bot_insta" / "config" / "history.json")
        self._cache = None

    def _load(self) -> list[dict]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("Failed to load history: %s", e)
            return []

    def _save(self, data: list[dict]) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._cache = data
        except Exception as e:
            log.error("Failed to save history: %s", e)

    def log_event(self, filename: str, platform: str, account_id: str, status: str, media_id: str = "") -> None:
        """
        Registers a generation/upload event into the history log.
        """
        now = datetime.now()
        entry = {
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            "filename": filename,
            "platform": platform,
            "account_id": account_id,
            "status": status,
            "media_id": media_id
        }
        
        data = self._cache if self._cache is not None else self._load()
        data.append(entry)
        self._save(data)

    def get_events_by_date(self, target_date: str) -> list[dict]:
        """
        Returns all events matching a specific date string (YYYY-MM-DD).
        """
        data = self._cache if self._cache is not None else self._load()
        # Sort so newest is first
        events = [e for e in data if e.get("date") == target_date]
        return sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)

    def get_all_active_dates(self) -> set[str]:
        """
        Returns a set of 'YYYY-MM-DD' strings that have at least one upload.
        Useful for highlighting dates on the calendar.
        """
        data = self._cache if self._cache is not None else self._load()
        return {e.get("date") for e in data if "date" in e}

# Singleton instance
history_manager = HistoryManager()
