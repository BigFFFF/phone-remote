from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .models import DiscoveredApp, program_candidate


class StartMenuProvider:
    source = "start-menu"

    def roots(self) -> list[Path]:
        values = []
        for environment, suffix in (
            ("APPDATA", Path("Microsoft/Windows/Start Menu/Programs")),
            ("PROGRAMDATA", Path("Microsoft/Windows/Start Menu/Programs")),
        ):
            base = os.environ.get(environment)
            if base:
                values.append(Path(base) / suffix)
        return values

    def discover(self) -> list[DiscoveredApp]:
        if sys.platform != "win32":
            return []
        roots = [str(value) for value in self.roots() if value.is_dir()]
        if not roots:
            return []
        script = r"""
$roots = ConvertFrom-Json $env:PHONE_REMOTE_SHORTCUT_ROOTS
$shell = New-Object -ComObject WScript.Shell
$result = foreach ($root in $roots) {
  Get-ChildItem -LiteralPath $root -Filter *.lnk -File -Recurse `
    -ErrorAction SilentlyContinue | ForEach-Object {
    try {
      $shortcut = $shell.CreateShortcut($_.FullName)
      [pscustomobject]@{
        name = $_.BaseName
        target = $shortcut.TargetPath
        arguments = $shortcut.Arguments
        workingDirectory = $shortcut.WorkingDirectory
        icon = $shortcut.IconLocation
      }
    } catch {}
  }
}
$result | ConvertTo-Json -Compress
"""
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        environment = os.environ.copy()
        environment["PHONE_REMOTE_SHORTCUT_ROOTS"] = json.dumps(roots)
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
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
        candidates = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            candidate = program_candidate(
                name=str(item.get("name", "")),
                executable=str(item.get("target", "")),
                arguments=_split_arguments(str(item.get("arguments", ""))),
                icon=_icon_path(str(item.get("icon", ""))),
                source=self.source,
                confidence=90,
            )
            if candidate:
                candidates.append(candidate)
        return candidates


def _split_arguments(value: str) -> list[str]:
    if not value.strip():
        return []
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        argc = ctypes.c_int()
        command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
        command_line_to_argv.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int))
        command_line_to_argv.restype = ctypes.POINTER(wintypes.LPWSTR)
        pointer = command_line_to_argv(value, ctypes.byref(argc))
        if pointer:
            try:
                return [pointer[index] for index in range(argc.value)][:32]
            finally:
                ctypes.windll.kernel32.LocalFree(pointer)
    return value.split()[:32]


def _icon_path(value: str) -> str | None:
    path = value.rsplit(",", 1)[0].strip().strip('"')
    return path if Path(os.path.expandvars(path)).is_file() else None
