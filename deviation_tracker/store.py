from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import Deviation, STATUS_OUVERTE


class DeviationStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _load_raw(self) -> list:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return list(data.get("deviations", []))

    def _save_raw(self, items: list) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump({"deviations": items}, fh, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def all(self) -> list:
        with self._lock:
            return [Deviation.from_dict(d) for d in self._load_raw()]

    def add(self, deviation: Deviation) -> Deviation:
        with self._lock:
            items = self._load_raw()
            items.append(deviation.to_dict())
            self._save_raw(items)
        return deviation

    def get(self, deviation_id: str):
        for dev in self.all():
            if dev.id == deviation_id:
                return dev
        return None

    def update_status(self, deviation_id: str, status: str) -> Deviation:
        with self._lock:
            items = self._load_raw()
            for item in items:
                if item.get("id") == deviation_id:
                    item["status"] = status
                    self._save_raw(items)
                    return Deviation.from_dict(item)
            raise KeyError(f"Deviation inconnue: {deviation_id}")

    def filter(self, team=None, status=None, since=None) -> list:
        result = self.all()
        if team:
            result = [d for d in result if d.team.lower() == team.lower()]
        if status and status != "toutes":
            result = [d for d in result if d.status == status]
        if since:
            since_prefix = since if "T" in since else since + "T00:00:00"
            result = [d for d in result if d.created_at >= since_prefix]
        result.sort(key=lambda d: d.created_at)
        return result

    def open(self, team=None, since=None) -> list:
        return self.filter(team=team, status=STATUS_OUVERTE, since=since)
