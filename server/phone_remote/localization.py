from __future__ import annotations

import locale
import os
from pathlib import Path


class UiLanguageStore:
    """Small shared preference used by the Windows tray and management page."""

    def __init__(self, path: Path):
        self.path = path

    def get(self) -> str:
        try:
            value = self.path.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value in {"zh", "en"}:
            return value
        system_language = (locale.getlocale()[0] or "").casefold()
        return "zh" if system_language.startswith("zh") else "en"

    def set(self, language: str) -> str:
        if language not in {"zh", "en"}:
            raise ValueError("language must be zh or en")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(language, encoding="utf-8")
        os.replace(temporary, self.path)
        return language
