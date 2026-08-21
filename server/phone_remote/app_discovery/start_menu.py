from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .models import DiscoveredApp, program_candidate
from .powershell import run_powershell_json

_BLOCKED_SHORTCUT_NAME = re.compile(
    r"^(?:"
    r"uninst(?:all|aller)?\b|remove\b|repair\b|modify\b|"
    r"check\s+for\s+updates?\b|updates?\b|"
    r".*\binstall\s+manager\b|.*\blanguage\s+preferences\b|"
    r"documentation\b|readme\b|release\s+notes?\b|online\s+help\b"
    r")",
    re.IGNORECASE,
)
_BLOCKED_CJK_NAME_PARTS = ("卸载", "移除", "修复", "更新程序", "帮助文档", "说明文档", "发行说明")
_BLOCKED_EXECUTABLE = re.compile(
    r"^(?:"
    r"unins\d*.*|uninst(?:all|aller)?.*|setup|installer|install|.*installmanager|"
    r"updater?|updateassistant|maintenancetool|repair|remove|modify|"
    r"crashreport(?:er)?|bugreport(?:tool)?|diagnostic(?:s)?|"
    r"vc_redist(?:\..+)?|aacsetup|onedrivesetup|officeclicktorun|msedgewebview2"
    r")$",
    re.IGNORECASE,
)
_BLOCKED_LAUNCHERS = {
    "cmd.exe",
    "control.exe",
    "cscript.exe",
    "msiexec.exe",
    "powershell.exe",
    "powershell_ise.exe",
    "regedit.exe",
    "rundll32.exe",
    "wscript.exe",
}


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
      $productName = ''
      $fileDescription = ''
      if ($shortcut.TargetPath -and (Test-Path -LiteralPath $shortcut.TargetPath -PathType Leaf)) {
        try {
          $version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($shortcut.TargetPath)
          $productName = $version.ProductName
          $fileDescription = $version.FileDescription
        } catch {}
      }
      [pscustomobject]@{
        name = $_.BaseName
        shortcut = $_.FullName
        target = $shortcut.TargetPath
        arguments = $shortcut.Arguments
        workingDirectory = $shortcut.WorkingDirectory
        icon = $shortcut.IconLocation
        productName = $productName
        fileDescription = $fileDescription
      }
    } catch {}
  }
}
$result | ConvertTo-Json -Compress
"""
        try:
            raw = run_powershell_json(
                script,
                environment={"PHONE_REMOTE_SHORTCUT_ROOTS": json.dumps(roots)},
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        entries = raw if isinstance(raw, list) else [raw]
        candidates = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            if not _is_user_facing_shortcut(item):
                continue
            target = str(item.get("target", ""))
            candidate = program_candidate(
                name=_best_name(item, Path(target).stem),
                executable=target,
                arguments=_split_arguments(str(item.get("arguments", ""))),
                icon=_icon_source(str(item.get("icon", ""))) or target,
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


def _is_user_facing_shortcut(item: dict[str, object]) -> bool:
    name = " ".join(str(item.get("name", "")).split()).strip()
    target_value = os.path.expandvars(str(item.get("target", "")).strip().strip('"'))
    target = Path(target_value)
    if not name or not target.is_absolute() or target.suffix.lower() != ".exe":
        return False

    target_name = target.name.casefold()
    target_stem = target.stem
    path_text = str(target).casefold()
    windows_root = Path(os.environ.get("WINDIR", r"C:\Windows"))
    try:
        if target.resolve().is_relative_to(windows_root.resolve()):
            return False
    except OSError:
        return False
    if "\\windowsapps\\" in path_text or "\\package cache\\" in path_text:
        return False
    if target_name in _BLOCKED_LAUNCHERS or _BLOCKED_EXECUTABLE.fullmatch(target_stem):
        return False
    if _BLOCKED_SHORTCUT_NAME.search(name):
        return False
    if any(part in name for part in _BLOCKED_CJK_NAME_PARTS):
        return False
    return target.is_file()


def _best_name(item: dict[str, object], fallback: str) -> str:
    values = (
        str(item.get("name", "")),
        str(item.get("productName", "")),
        str(item.get("fileDescription", "")),
        fallback,
    )
    return next((value for value in values if _readable_name(value)), fallback)


def _readable_name(value: str) -> bool:
    cleaned = " ".join(value.split()).strip()
    return (
        bool(cleaned)
        and "\ufffd" not in cleaned
        and all(character.isprintable() for character in cleaned)
    )


def _icon_source(value: str) -> str | None:
    raw = os.path.expandvars(value.strip())
    match = re.fullmatch(r'"?(.*?)"?\s*(?:,\s*(-?\d+))?', raw)
    if not match:
        return None
    path = Path(match.group(1))
    if not path.is_file():
        return None
    index = match.group(2)
    return f"{path},{index}" if index is not None else str(path)
