import json
import logging
import uuid
from pathlib import Path
from datetime import datetime

from bot_insta.src.core.config_loader import PROJECT_ROOT

log = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, scheduler_file: Path = None):
        self.scheduler_file = scheduler_file or (PROJECT_ROOT / "bot_insta" / "config" / "scheduler.json")
        self._cache = None
        self._lock = __import__('threading').Lock()

    def _load(self) -> list[dict]:
        if not self.scheduler_file.exists():
            return []
        try:
            with open(self.scheduler_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error("Failed to load scheduler: %s", e)
            return []

    def _save(self, data: list[dict]) -> None:
        self.scheduler_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.scheduler_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._cache = data
        except Exception as e:
            log.error("Failed to save scheduler: %s", e)

    def add_job(self, type: str, profile: str, account_id: str, platform: str, caption: str, scheduled_time: str, file_path: str = "", quotes_override: str = "", batch_id: str = "") -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "batch_id": batch_id or "Ungrouped",
            "type": type,
            "profile": profile,
            "account_id": account_id,
            "platform": platform,
            "caption": caption,
            "scheduled_time": scheduled_time,
            "file_path": file_path,
            "quotes_override": quotes_override,
            "status": "pending",
            "error_msg": ""
        }
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
            data.append(entry)
            self._save(data)
        return entry

    def update_job_status(self, job_id: str, status: str, error_msg: str = ""):
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
            for job in data:
                if job["id"] == job_id:
                    job["status"] = status
                    if error_msg:
                        job["error_msg"] = error_msg
                    break
            self._save(data)
        
    def update_job_file(self, job_id: str, file_path: str):
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
            for job in data:
                if job["id"] == job_id:
                    job["file_path"] = file_path
                    break
            self._save(data)

    def delete_job(self, job_id: str):
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
            data = [j for j in data if j["id"] != job_id]
            self._save(data)

    def get_all_jobs(self) -> list[dict]:
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
        # Sort by scheduled time
        return sorted(data, key=lambda x: x.get("scheduled_time", ""))

    def get_pending_jobs(self) -> list[dict]:
        with self._lock:
            data = self._cache if self._cache is not None else self._load()
        now = datetime.now().isoformat()
        pending = [j for j in data if j.get("status") == "pending" and j.get("scheduled_time", "") <= now]
        return sorted(pending, key=lambda x: x.get("scheduled_time", ""))

scheduler_manager = SchedulerManager()
