"""
account_manager.py
─────────────────────────────────────────────────────────────────────────────
Handles multi-platform account linked storage and statuses.
"""

import os
import json
import uuid
import logging
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent
ACCOUNTS_FILE = PROJECT_ROOT / "bot_insta" / "config" / "accounts.json"

log = logging.getLogger(__name__)

class AccountManager:
    def __init__(self, filepath: Path = ACCOUNTS_FILE):
        self.filepath = filepath
        self.accounts = self._load()

    def _load(self) -> list[dict]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error loading accounts: {e}")
            return []

    def _save(self) -> None:
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, indent=4)
        except Exception as e:
            log.error(f"Error saving accounts: {e}")

    def list_accounts(self) -> list[dict]:
        return self.accounts

    def add_account(self, name: str, platform: str, credentials: dict) -> dict:
        acc = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "platform": platform,
            "status": "Unknown",
            "credentials": credentials
        }
        self.accounts.append(acc)
        self._save()
        return acc

    def delete_account(self, acc_id: str) -> None:
        self.accounts = [a for a in self.accounts if a["id"] != acc_id]
        self._save()

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
