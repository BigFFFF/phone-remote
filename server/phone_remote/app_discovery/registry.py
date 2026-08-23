from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .models import DiscoveredApp, program_candidate

if sys.platform == "win32":
    import winreg


_AUXILIARY_EXECUTABLE = re.compile(
    r"^(?:unins\d*.*|uninst(?:all|aller)?.*|setup|installer|install|"
    r"maintenancetool|repair|remove|modify)$",
    re.IGNORECASE,
)
_AUXILIARY_NAME_PARTS = ("卸载", "移除", "修复")


class RegistryProvider:
    source = "registry-uninstall"
    LOCATIONS = (
        ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ("HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    )

    def discover(self) -> list[DiscoveredApp]:
        if sys.platform != "win32":
            return []
        candidates = []
        for hive_name, location in self.LOCATIONS:
            hive = winreg.HKEY_LOCAL_MACHINE if hive_name == "HKLM" else winreg.HKEY_CURRENT_USER
            try:
                root = winreg.OpenKey(hive, location)
            except OSError:
                continue
            with root:
                for index in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        child_name = winreg.EnumKey(root, index)
                        child = winreg.OpenKey(root, child_name)
                    except OSError:
                        continue
                    with child:
                        name = _query(child, "DisplayName")
                        display_icon = _query(child, "DisplayIcon")
                        if not name or not display_icon:
                            continue
                        executable = _display_icon_executable(display_icon)
                        if not _is_launchable_registry_entry(name, executable):
                            continue
                        candidate = program_candidate(
                            name=name,
                            executable=executable,
                            icon=executable,
                            source=self.source,
                            confidence=55,
                        )
                        if candidate:
                            candidates.append(candidate)
        return candidates


def _query(key, name: str) -> str:
    try:
        value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return str(value) if isinstance(value, str) else ""


def _display_icon_executable(value: str) -> str:
    expanded = os.path.expandvars(value.strip())
    if expanded.startswith('"'):
        closing = expanded.find('"', 1)
        return expanded[1:closing] if closing > 1 else ""
    candidate = expanded.rsplit(",", 1)[0]
    return str(Path(candidate.strip()))


def _is_launchable_registry_entry(name: str, executable: str) -> bool:
    """Reject uninstall/maintenance binaries exposed as uninstall DisplayIcon values."""
    cleaned_name = " ".join(name.split()).strip()
    stem = Path(executable).stem
    if not cleaned_name or not executable or _AUXILIARY_EXECUTABLE.fullmatch(stem):
        return False
    lowered = cleaned_name.casefold()
    if re.search(r"\b(?:uninstall|uninstaller|remove|repair)\b", lowered):
        return False
    return not any(part in cleaned_name for part in _AUXILIARY_NAME_PARTS)
