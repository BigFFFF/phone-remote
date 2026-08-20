from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .models import DiscoveredApp


@dataclass(frozen=True)
class KnownApp:
    app_id: str
    display_aliases: tuple[str, ...]
    executable_aliases: tuple[str, ...]
    category: str
    recommended_arguments: tuple[str, ...] = ()


KNOWN_APPS = (
    KnownApp(
        "steam", ("steam",), ("steam.exe",), "Games / Launchers", ("steam://open/bigpicture",)
    ),
    KnownApp("edge", ("microsoft edge", "edge"), ("msedge.exe",), "Browsers"),
    KnownApp("chrome", ("google chrome", "chrome"), ("chrome.exe",), "Browsers"),
    KnownApp("firefox", ("mozilla firefox", "firefox"), ("firefox.exe",), "Browsers"),
    KnownApp("vlc", ("vlc media player", "vlc"), ("vlc.exe",), "Media Players"),
    KnownApp("spotify", ("spotify",), ("spotify.exe",), "Music"),
    KnownApp("kodi", ("kodi",), ("kodi.exe",), "Media Players"),
)


def match_known_app(candidate: DiscoveredApp) -> KnownApp | None:
    name = candidate.name.casefold()
    executable = ""
    if candidate.launch["type"] == "program":
        executable = Path(os.path.expandvars(candidate.launch["path"])).name.casefold()
    for known in KNOWN_APPS:
        if executable in known.executable_aliases or name in known.display_aliases:
            return known
    return None


def apply_known_app(candidate: DiscoveredApp) -> DiscoveredApp:
    known = match_known_app(candidate)
    if known is None:
        return candidate
    candidate.known_app_id = known.app_id
    candidate.category = known.category
    candidate.confidence = max(candidate.confidence, 90)
    if (
        candidate.launch["type"] == "program"
        and known.recommended_arguments
        and not candidate.launch.get("args")
    ):
        candidate.launch["args"] = list(known.recommended_arguments)
    return candidate
