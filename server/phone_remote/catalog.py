from __future__ import annotations

import os
import re
import shutil
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .app_discovery import ApplicationDiscovery, DiscoveredApp
from .config import APP_ID_PATTERN, ConfigStore

DEFAULT_ICON = "default.svg"


class ApplicationCatalog:
    def __init__(
        self,
        config: ConfigStore,
        discovery: ApplicationDiscovery,
        bundled_default_icon: Path,
    ):
        self.config = config
        self.discovery = discovery
        self.bundled_default_icon = bundled_default_icon
        self._lock = threading.RLock()
        self._candidates: dict[str, DiscoveredApp] = {}

    def rescan(self) -> list[dict[str, Any]]:
        with self._lock:
            candidates = self.discovery.scan()
            self._candidates = {item.discovery_id: item for item in candidates}
            self._update_availability(candidates)
            configured_identities = {
                _launch_identity(item["launch"]) for item in self.config.get()["apps"]
            }
            return [
                {
                    **item.public(),
                    "configured": _launch_identity(item.launch) in configured_identities,
                }
                for item in candidates
            ]

    def candidates(self) -> list[dict[str, Any]]:
        with self._lock:
            return [item.public() for item in self._candidates.values()]

    def approve(self, discovery_id: str) -> dict[str, Any]:
        with self._lock:
            candidate = self._candidates.get(discovery_id)
            if candidate is None:
                raise ValueError("unknown discovered app; rescan first")
            config = self.config.get()
            identity = _launch_identity(candidate.launch)
            if any(_launch_identity(item["launch"]) == identity for item in config["apps"]):
                raise ValueError("app is already configured")
            app_id = self._unique_id(candidate.known_app_id or candidate.name, config)
            icon = self._import_icon(candidate.icon, app_id)
            app = {
                "id": app_id,
                "name": candidate.name,
                "enabled": True,
                "available": True,
                "icon": icon,
                "launch": candidate.launch,
            }
            config["apps"].append(app)
            self.config.write(config)
            return app

    def add_program(
        self, name: str, path: str, arguments: list[str] | None = None
    ) -> dict[str, Any]:
        executable = Path(os.path.expandvars(path))
        if (
            not executable.is_absolute()
            or executable.suffix.lower() != ".exe"
            or not executable.is_file()
        ):
            raise ValueError("manual program must be an existing absolute .exe path")
        arguments = arguments or []
        if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
            raise ValueError("invalid program arguments")
        return self._add_manual(
            name,
            {"type": "program", "path": str(executable.resolve()), "args": arguments},
        )

    def add_website(
        self, name: str, browser: str, url: str, *, fullscreen: bool = False
    ) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("website URL must use http or https")
        config = self.config.get()
        if browser not in config["browsers"]:
            raise ValueError("unknown browser")
        return self._add_manual(
            name,
            {"type": "browser", "browser": browser, "url": url, "fullscreen": fullscreen},
        )

    def set_enabled(self, app_id: str, enabled: bool) -> dict[str, Any]:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false")
        config = self.config.get()
        app = next((item for item in config["apps"] if item["id"] == app_id), None)
        if app is None:
            raise ValueError("unknown app")
        app["enabled"] = enabled
        self.config.write(config)
        return app

    def remove(self, app_id: str) -> bool:
        config = self.config.get()
        remaining = [item for item in config["apps"] if item["id"] != app_id]
        if len(remaining) == len(config["apps"]):
            return False
        config["apps"] = remaining
        self.config.write(config)
        return True

    def _add_manual(self, name: str, launch: dict[str, Any]) -> dict[str, Any]:
        name = " ".join(str(name).split())[:80]
        if not name:
            raise ValueError("invalid app name")
        config = self.config.get()
        if any(
            _launch_identity(item["launch"]) == _launch_identity(launch) for item in config["apps"]
        ):
            raise ValueError("app is already configured")
        app = {
            "id": self._unique_id(name, config),
            "name": name,
            "enabled": True,
            "available": True,
            "icon": self._import_icon(None, "manual"),
            "launch": launch,
        }
        config["apps"].append(app)
        self.config.write(config)
        return app

    def _update_availability(self, candidates: list[DiscoveredApp]) -> None:
        identities = {_launch_identity(item.launch) for item in candidates}
        config = self.config.get()
        changed = False
        for app in config["apps"]:
            launch = app["launch"]
            available = True
            if launch["type"] in {"program", "appx"}:
                available = _launch_identity(launch) in identities
                if (
                    launch["type"] == "program"
                    and Path(os.path.expandvars(launch["path"])).is_file()
                ):
                    available = True
            if app.get("available", True) != available:
                app["available"] = available
                changed = True
        if changed:
            self.config.write(config)

    def _import_icon(self, source_value: str | None, app_id: str) -> str:
        self.config.icon_root.mkdir(parents=True, exist_ok=True)
        if source_value:
            source = Path(os.path.expandvars(source_value.split(",", 1)[0].strip().strip('"')))
            if source.is_file() and source.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".svg",
                ".webp",
            }:
                destination = self.config.icon_root / f"{app_id}{source.suffix.lower()}"
                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
                return destination.name
        destination = self.config.icon_root / DEFAULT_ICON
        if not destination.exists():
            shutil.copy2(self.bundled_default_icon, destination)
        return DEFAULT_ICON

    @staticmethod
    def _unique_id(value: str, config: dict[str, Any]) -> str:
        base = re.sub(r"[^a-z0-9_-]+", "-", value.casefold()).strip("-_")[:24] or "app"
        if not APP_ID_PATTERN.fullmatch(base):
            base = "app"
        existing = {item["id"] for item in config["apps"]}
        candidate = base
        counter = 2
        while candidate in existing:
            candidate = f"{base[:27]}-{counter}"
            counter += 1
        return candidate


def _launch_identity(launch: dict[str, Any]) -> str:
    if launch["type"] == "program":
        return "program:" + os.path.normcase(os.path.expandvars(launch["path"]))
    if launch["type"] == "appx":
        return "appx:" + launch["appUserModelId"].lower()
    return "browser:" + launch["browser"] + ":" + launch.get("url", "")
