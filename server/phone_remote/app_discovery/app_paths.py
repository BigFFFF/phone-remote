from __future__ import annotations

import sys

from .models import DiscoveredApp, program_candidate

if sys.platform == "win32":
    import winreg


class AppPathsProvider:
    source = "app-paths"
    LOCATION = r"Software\Microsoft\Windows\CurrentVersion\App Paths"

    def discover(self) -> list[DiscoveredApp]:
        if sys.platform != "win32":
            return []
        candidates = []
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    root = winreg.OpenKey(hive, self.LOCATION, 0, winreg.KEY_READ | view)
                except OSError:
                    continue
                with root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            child_name = winreg.EnumKey(root, index)
                            with winreg.OpenKey(root, child_name) as child:
                                executable, _ = winreg.QueryValueEx(child, None)
                        except OSError:
                            continue
                        candidate = program_candidate(
                            name=child_name.removesuffix(".exe"),
                            executable=str(executable),
                            source=self.source,
                            confidence=70,
                        )
                        if candidate:
                            candidates.append(candidate)
        return candidates
