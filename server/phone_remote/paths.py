from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    bundle_root: Path
    executable_root: Path
    data_root: Path
    config_path: Path
    icon_root: Path
    state_path: Path
    identity_key_path: Path
    certificate_path: Path
    tls_key_path: Path
    log_root: Path
    web_root: Path

    @classmethod
    def resolve(cls) -> RuntimePaths:
        frozen = bool(getattr(sys, "frozen", False))
        if frozen:
            bundle_root = Path(sys._MEIPASS).resolve()
            executable_root = Path(sys.executable).resolve().parent
        else:
            bundle_root = Path(__file__).resolve().parent.parent
            executable_root = bundle_root.parent

        configured_data = os.environ.get("PHONE_REMOTE_DATA_DIR")
        if configured_data:
            data_root = Path(os.path.expandvars(configured_data)).expanduser().resolve()
        else:
            local_app_data = os.environ.get("LOCALAPPDATA")
            base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
            data_root = (base / "PhoneRemote").resolve()

        configured_config = os.environ.get("PHONE_REMOTE_CONFIG")
        config_path = (
            Path(os.path.expandvars(configured_config)).expanduser().resolve()
            if configured_config
            else data_root / "config.json"
        )
        icon_root = config_path.parent / "icons"
        return cls(
            bundle_root=bundle_root,
            executable_root=executable_root,
            data_root=data_root,
            config_path=config_path,
            icon_root=icon_root,
            state_path=data_root / "state.json",
            identity_key_path=data_root / "server-identity.key",
            certificate_path=data_root / "server.crt",
            tls_key_path=data_root / "server.key",
            log_root=data_root / "logs",
            web_root=bundle_root / "web",
        )

    def prepare(self) -> list[str]:
        """Create private user storage and migrate only when the destination is absent."""
        events: list[str] = []
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.log_root.mkdir(parents=True, exist_ok=True)
        self.icon_root.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            legacy = self.executable_root / "config.json"
            example_candidates = [
                self.bundle_root / "config.example.json",
                self.executable_root / "config.example.json",
            ]
            source = (
                legacy
                if legacy.is_file()
                else next((item for item in example_candidates if item.is_file()), None)
            )
            if source is not None:
                shutil.copy2(source, self.config_path)
                events.append(f"copied config from {source}")

        legacy_icons = self.executable_root / "icons"
        bundled_icons = self.bundle_root / "resources" / "icons"
        for source_root in (legacy_icons, bundled_icons):
            if not source_root.is_dir():
                continue
            for source in source_root.iterdir():
                destination = self.icon_root / source.name
                if source.is_file() and not destination.exists():
                    shutil.copy2(source, destination)
            events.append(f"copied missing icons from {source_root}")
        return events
