from __future__ import annotations

import copy
import json
import os
import re
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

APP_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
AUMID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,160}![A-Za-z0-9._-]{1,80}$")
ICON_SUFFIXES = {".jpg", ".jpeg", ".png", ".svg", ".webp"}
DEFAULT_CONFIG = {
    "version": 1,
    "initialDiscoveryComplete": False,
    "browsers": {},
    "apps": [],
}


def require_text(value: Any, field: str, max_length: int = 260) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"invalid {field}")
    return value.strip()


def require_arguments(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if (
        not isinstance(value, list)
        or len(value) > 32
        or not all(isinstance(item, str) and len(item) <= 2048 for item in value)
    ):
        raise ValueError(f"invalid {field}")
    return list(value)


def require_absolute_path(value: Any, field: str) -> str:
    path = require_text(value, field, 1024)
    if not Path(os.path.expandvars(path)).is_absolute():
        raise ValueError(f"{field} must be an absolute path")
    return path


def validate_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("config must be an object")
    if raw.get("version") != 1:
        raise ValueError("unsupported config version")
    initial_discovery_complete = raw.get("initialDiscoveryComplete", False)
    if not isinstance(initial_discovery_complete, bool):
        raise ValueError("initialDiscoveryComplete must be true or false")
    browser_source = raw.get("browsers", {})
    if not isinstance(browser_source, dict):
        raise ValueError("browsers must be an object")
    browsers: dict[str, dict[str, Any]] = {}
    for browser_id, value in browser_source.items():
        if not APP_ID_PATTERN.fullmatch(str(browser_id)) or not isinstance(value, dict):
            raise ValueError("invalid browser entry")
        browsers[str(browser_id)] = {
            "path": require_absolute_path(value.get("path"), "browser path"),
            "args": require_arguments(value.get("args"), "browser args"),
            "fullscreenArgs": require_arguments(
                value.get("fullscreenArgs"), "browser fullscreenArgs"
            ),
        }

    app_source = raw.get("apps")
    if not isinstance(app_source, list):
        raise ValueError("apps must be an array")
    apps: list[dict[str, Any]] = []
    app_ids: set[str] = set()
    for value in app_source:
        if not isinstance(value, dict):
            raise ValueError("invalid app entry")
        app_id = require_text(value.get("id"), "app id", 32)
        if not APP_ID_PATTERN.fullmatch(app_id) or app_id in app_ids:
            raise ValueError(f"invalid or duplicate app id: {app_id}")
        app_ids.add(app_id)

        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false")
        available = value.get("available", True)
        if not isinstance(available, bool):
            raise ValueError("available must be true or false")
        icon = require_text(value.get("icon"), "app icon", 128)
        if Path(icon).name != icon or Path(icon).suffix.lower() not in ICON_SUFFIXES:
            raise ValueError(f"invalid app icon: {icon}")

        launch_source = value.get("launch")
        if not isinstance(launch_source, dict):
            raise ValueError(f"invalid launch settings: {app_id}")
        launch_type = launch_source.get("type")
        if launch_type == "program":
            launch = {
                "type": "program",
                "path": require_absolute_path(launch_source.get("path"), "program path"),
                "args": require_arguments(launch_source.get("args"), "program args"),
            }
        elif launch_type == "browser":
            browser_id = require_text(launch_source.get("browser"), "browser id", 32)
            if browser_id not in browsers:
                raise ValueError(f"unknown browser: {browser_id}")
            url = launch_source.get("url", "")
            if not isinstance(url, str) or len(url) > 2048:
                raise ValueError("invalid browser URL")
            if url:
                parsed_url = urlparse(url)
                if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc:
                    raise ValueError("browser URL must use an absolute http or https URL")
            fullscreen = launch_source.get("fullscreen", False)
            if not isinstance(fullscreen, bool):
                raise ValueError("fullscreen must be true or false")
            launch = {
                "type": "browser",
                "browser": browser_id,
                "url": url,
                "fullscreen": fullscreen,
            }
        elif launch_type == "appx":
            app_user_model_id = require_text(
                launch_source.get("appUserModelId"), "app user model id", 240
            )
            if not AUMID_PATTERN.fullmatch(app_user_model_id):
                raise ValueError("invalid app user model id")
            launch = {"type": "appx", "appUserModelId": app_user_model_id}
        else:
            raise ValueError(f"unknown launch type: {launch_type}")

        apps.append(
            {
                "id": app_id,
                "name": require_text(value.get("name"), "app name", 80),
                "enabled": enabled,
                "icon": icon,
                "available": available,
                "launch": launch,
            }
        )
    return {
        "version": 1,
        "initialDiscoveryComplete": initial_discovery_complete,
        "browsers": browsers,
        "apps": apps,
    }


class ConfigStore:
    def __init__(self, path: Path, icon_root: Path):
        self.path = path
        self.icon_root = icon_root
        self._lock = threading.RLock()
        self._signature: object = None
        self._config: dict[str, Any] | None = None
        self._error: str | None = None

    def initialize(self) -> bool:
        """Create the single runtime configuration file when it is absent."""
        with self._lock:
            if self.path.is_file():
                return False
            self.write(copy.deepcopy(DEFAULT_CONFIG))
            return True

    def _file_signature(self) -> object:
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return "missing", str(self.path)

    def get(self) -> dict[str, Any]:
        with self._lock:
            signature = self._file_signature()
            if signature == self._signature and self._config is not None:
                return copy.deepcopy(self._config)
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
                config = validate_config(raw)
            except Exception as exc:
                self._signature = signature
                self._error = str(exc)
                if self._config is None:
                    raise ValueError(f"config error: {exc}") from exc
                return copy.deepcopy(self._config)
            self._signature = signature
            self._config = config
            self._error = None
            return copy.deepcopy(config)

    def write(self, config: dict[str, Any]) -> None:
        normalized = validate_config(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, self.path)
        with self._lock:
            self._signature = None

    @property
    def error(self) -> str | None:
        self.get()
        return self._error

    def public_apps(self) -> list[dict[str, Any]]:
        result = []
        for app in self.get()["apps"]:
            if not app["enabled"]:
                continue
            available = bool(app.get("available", True))
            if app["launch"]["type"] == "program":
                available = available and Path(os.path.expandvars(app["launch"]["path"])).is_file()
            icon_path = self.icon_root / app["icon"]
            try:
                icon_version = icon_path.stat().st_mtime_ns
            except OSError:
                icon_version = 0
            result.append(
                {
                    "id": app["id"],
                    "name": app["name"],
                    "available": available,
                    "icon": f"/app-icons/{quote(app['icon'], safe='')}?v={icon_version}",
                }
            )
        return result
