import json
import yaml
import logging
from typing import Any
from pathlib import Path
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

class IStorage(ABC):
    @abstractmethod
    def load(self, filepath: Path) -> Any:
        pass

    @abstractmethod
    def save(self, filepath: Path, data: Any) -> None:
        pass

class JsonStorage(IStorage):
    def load(self, filepath: Path) -> Any:
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error loading JSON {filepath}: {e}")
            return None

    def save(self, filepath: Path, data: Any) -> None:
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            log.error(f"Error saving JSON {filepath}: {e}")

class YamlStorage(IStorage):
    def load(self, filepath: Path) -> Any:
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log.error(f"Error loading YAML {filepath}: {e}")
            return None

    def save(self, filepath: Path, data: Any) -> None:
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            log.error(f"Error saving YAML {filepath}: {e}")
