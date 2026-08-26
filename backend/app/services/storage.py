import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, data_path: Path, seed_path: Path):
        self.data_path = data_path
        self.seed_path = seed_path
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        path = self.data_path if self.data_path.exists() else self.seed_path
        with path.open("r", encoding="utf-8") as file:
            state = json.load(file)
        state.setdefault("documents", [])
        state.setdefault("feedback", [])
        state.setdefault("agent_tasks", [])
        state.setdefault("chat_count", 0)
        return state

    def _save(self) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.data_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(self._state, file, ensure_ascii=False, indent=2)
        temporary.replace(self.data_path)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def documents(self) -> list[dict[str, Any]]:
        return self.snapshot()["documents"]

    def add_document(self, document: dict[str, Any]) -> None:
        with self._lock:
            self._state["documents"].append(deepcopy(document))
            self._save()

    def feedback(self) -> list[dict[str, Any]]:
        return self.snapshot()["feedback"]

    def add_feedback(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._state["feedback"].append(deepcopy(record))
            self._save()

    def add_agent_task(self, task: dict[str, Any]) -> None:
        with self._lock:
            self._state["agent_tasks"].append(deepcopy(task))
            self._save()

    def agent_tasks(self) -> list[dict[str, Any]]:
        return self.snapshot()["agent_tasks"]

    def agent_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            for task in self._state["agent_tasks"]:
                if task["id"] == task_id:
                    return deepcopy(task)
        return None

    def increment_chat_count(self) -> None:
        with self._lock:
            self._state["chat_count"] += 1
            self._save()
