from __future__ import annotations

import copy
import json
import os
import threading
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any


def _default_state() -> dict[str, Any]:
    return {"version": 1, "server": {}, "clients": []}


def _validate_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("unsupported state version")
    if not isinstance(value.get("server"), dict):
        raise ValueError("state server must be an object")
    if not isinstance(value.get("clients"), list):
        raise ValueError("state clients must be an array")
    return value


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()

    def read(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return _default_state()
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
            return copy.deepcopy(_validate_state(raw))

    def write(self, value: dict[str, Any]) -> None:
        with self._lock:
            normalized = copy.deepcopy(_validate_state(value))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            with suppress(OSError):
                os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)

    def update(self, mutate: Callable[[dict[str, Any]], Any]) -> Any:
        with self._lock:
            state = self.read()
            result = mutate(state)
            self.write(state)
            return result
