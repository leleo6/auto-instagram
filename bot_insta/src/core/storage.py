import json
import shutil
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
            log.error("Error loading JSON %s: %s", filepath, e)
            return None

    def save(self, filepath: Path, data: Any) -> None:
        # EC-10 fix: escritura atómica — escribir a .tmp y renombrar al destino.
        # Evita dejar el archivo corrupto si el proceso es interrumpido.
        tmp = filepath.with_suffix(".json.tmp")
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            shutil.move(str(tmp), str(filepath))  # Rename atómico
        except Exception as e:
            tmp.unlink(missing_ok=True)
            log.error("Error saving JSON %s: %s", filepath, e)

class YamlStorage(IStorage):
    def load(self, filepath: Path) -> Any:
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log.error("Error loading YAML %s: %s", filepath, e)
            return None

    def save(self, filepath: Path, data: Any) -> None:
        # EC-10 fix: escritura atómica — escribir a .tmp y renombrar al destino.
        tmp = filepath.with_suffix(".yaml.tmp")
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            shutil.move(str(tmp), str(filepath))  # Rename atómico
        except Exception as e:
            tmp.unlink(missing_ok=True)
            log.error("Error saving YAML %s: %s", filepath, e)
