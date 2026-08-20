from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from .models import DiscoveredApp, appx_candidate


class MsixProvider:
    source = "msix"

    def discover(self) -> list[DiscoveredApp]:
        if sys.platform != "win32":
            return []
        script = "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            shell=False,
        )
        if result.returncode or not result.stdout.strip():
            return []
        try:
            raw: Any = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        entries = raw if isinstance(raw, list) else [raw]
        result_apps = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            candidate = appx_candidate(
                name=str(item.get("Name", "")),
                app_user_model_id=str(item.get("AppID", "")),
                source=self.source,
            )
            if candidate:
                result_apps.append(candidate)
        return result_apps
