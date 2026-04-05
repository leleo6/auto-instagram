"""
account_manager.py
─────────────────────────────────────────────────────────────────────────────
Handles multi-platform account linked storage and statuses.
"""

import os
import uuid
import logging
from pathlib import Path

from bot_insta.src.core.storage import IStorage, JsonStorage

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent
ACCOUNTS_FILE = PROJECT_ROOT / "bot_insta" / "config" / "accounts.json"

log = logging.getLogger(__name__)

class AccountManager:
    def __init__(self, filepath: Path = ACCOUNTS_FILE, storage: IStorage = None):
        self.filepath = filepath
        self.storage = storage or JsonStorage()
        self.accounts = self._load()

    def _load(self) -> list[dict]:
        data = self.storage.load(self.filepath)
        if data is None:
            return []
        return data

    def _save(self) -> None:
        self.storage.save(self.filepath, self.accounts)

    def list_accounts(self) -> list[dict]:
        return self.accounts

    def add_account(self, name: str, platform: str, credentials: dict, proxy: str = "") -> dict:
        acc = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "platform": platform,
            "status": "Unknown",
            "credentials": credentials,
            "proxy": proxy
        }
        self.accounts.append(acc)
        self._save()
        return acc

    def delete_account(self, acc_id: str) -> None:
        self.accounts = [a for a in self.accounts if a["id"] != acc_id]
        self._save()

    def update_account(self, acc_id: str, **kwargs) -> bool:
        for a in self.accounts:
            if a["id"] == acc_id:
                for key, value in kwargs.items():
                    a[key] = value
                self._save()
                return True
        return False

    def update_status(self, acc_id: str, status: str) -> None:
        for a in self.accounts:
            if a["id"] == acc_id:
                a["status"] = status
                break
        self._save()

    def get_account(self, acc_id: str) -> dict:
        for a in self.accounts:
            if a["id"] == acc_id:
                return a
        return {}

    def fetch_options_for_dropdown(self) -> list[dict]:
        opts = [{"id": "local", "label": "Local (no upload)", "platform": "Local"}]
        for a in self.accounts:
            alias = a.get("name", "Account")
            opts.append({"id": a["id"], "label": alias, "platform": a["platform"]})
        return opts

# Global instance
acc_manager = AccountManager()
