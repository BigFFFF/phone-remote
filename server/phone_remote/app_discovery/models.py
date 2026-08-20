from __future__ import annotations

import hashlib
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DiscoveredApp:
    discovery_id: str
    name: str
    launch: dict[str, Any]
    source: str
    category: str = "Other"
    confidence: int = 50
    icon: str | None = None
    known_app_id: str | None = None
    sources: list[str] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        value["discoveryId"] = value.pop("discovery_id")
        value["knownAppId"] = value.pop("known_app_id")
        return value


def program_candidate(
    *,
    name: str,
    executable: str,
    source: str,
    arguments: list[str] | None = None,
    icon: str | None = None,
    confidence: int = 50,
) -> DiscoveredApp | None:
    expanded = Path(os.path.expandvars(executable.strip().strip('"')))
    if not expanded.is_absolute() or expanded.suffix.lower() != ".exe" or not expanded.is_file():
        return None
    identity = os.path.normcase(str(expanded.resolve()))
    return DiscoveredApp(
        discovery_id=_discovery_id("program", identity),
        name=_clean_name(name, expanded.stem),
        launch={
            "type": "program",
            "path": str(expanded.resolve()),
            "args": list(arguments or []),
        },
        source=source,
        sources=[source],
        icon=icon,
        confidence=confidence,
    )


def appx_candidate(*, name: str, app_user_model_id: str, source: str) -> DiscoveredApp | None:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,160}![A-Za-z0-9._-]{1,80}", app_user_model_id):
        return None
    return DiscoveredApp(
        discovery_id=_discovery_id("appx", app_user_model_id.lower()),
        name=_clean_name(name, app_user_model_id.partition("!")[0]),
        launch={"type": "appx", "appUserModelId": app_user_model_id},
        source=source,
        sources=[source],
        confidence=75,
    )


def candidate_identity(candidate: DiscoveredApp) -> str:
    launch = candidate.launch
    if launch["type"] == "program":
        return "program:" + os.path.normcase(os.path.expandvars(launch["path"]))
    return "appx:" + launch["appUserModelId"].lower()


def _discovery_id(kind: str, identity: str) -> str:
    digest = hashlib.sha256(f"{kind}\0{identity}".encode()).hexdigest()[:20]
    return f"{kind}-{digest}"


def _clean_name(value: str, fallback: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    return (cleaned or fallback)[:80]
