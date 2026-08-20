from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
import sys
import winreg
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_FIREWALL_RULE = "Phone Remote API"
DISCOVERY_FIREWALL_RULE = "Phone Remote Discovery"
STARTUP_VALUE_NAME = "Phone Remote"


def local_ipv4_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127.") and address not in addresses:
                addresses.append(address)
    except socket.gaierror:
        pass
    return addresses


def is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class NetworkProfile:
    name: str
    category: str
    ipv4_connectivity: str


class NetworkDiagnostics:
    def profiles(self) -> list[NetworkProfile]:
        if sys.platform != "win32":
            return []
        script = (
            "Get-NetConnectionProfile | Select-Object Name,NetworkCategory,IPv4Connectivity "
            "| ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            shell=False,
        )
        if result.returncode or not result.stdout.strip():
            return []
        try:
            value: Any = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        entries = value if isinstance(value, list) else [value]
        return [
            NetworkProfile(
                str(item.get("Name", "Unknown")),
                str(item.get("NetworkCategory", "Unknown")),
                str(item.get("IPv4Connectivity", "Unknown")),
            )
            for item in entries
            if isinstance(item, dict)
        ]

    def public_only(self) -> bool:
        connected = [
            item
            for item in self.profiles()
            if item.ipv4_connectivity.lower() not in {"disconnected", "none"}
        ]
        return bool(connected) and all(item.category.lower() == "public" for item in connected)

    def firewall_status(self) -> dict[str, bool | None]:
        if sys.platform != "win32":
            return {"api": None, "discovery": None}
        result: dict[str, bool | None] = {}
        for key, name in (("api", API_FIREWALL_RULE), ("discovery", DISCOVERY_FIREWALL_RULE)):
            command = [
                "netsh",
                "advfirewall",
                "firewall",
                "show",
                "rule",
                f"name={name}",
            ]
            completed = subprocess.run(
                command, capture_output=True, timeout=10, check=False, shell=False
            )
            result[key] = completed.returncode == 0
        return result


def firewall_install_commands(executable: Path, port: int) -> list[list[str]]:
    program = str(executable.resolve())
    return [
        firewall_remove_command(API_FIREWALL_RULE),
        firewall_remove_command(DISCOVERY_FIREWALL_RULE),
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={API_FIREWALL_RULE}",
            "dir=in",
            "action=allow",
            f"program={program}",
            "protocol=TCP",
            f"localport={port}",
            "profile=private",
            "remoteip=LocalSubnet",
            "enable=yes",
        ],
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={DISCOVERY_FIREWALL_RULE}",
            "dir=in",
            "action=allow",
            f"program={program}",
            "protocol=UDP",
            "localport=5353",
            "profile=private",
            "remoteip=LocalSubnet",
            "enable=yes",
        ],
    ]


def firewall_remove_command(name: str) -> list[str]:
    return ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"]


def set_start_with_windows(command: Path | Sequence[str], enabled: bool) -> None:
    if sys.platform != "win32":
        raise OSError("startup registration is only available on Windows")
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, access=winreg.KEY_SET_VALUE) as key:
        if enabled:
            arguments = [str(command.resolve())] if isinstance(command, Path) else list(command)
            if not arguments or not all(isinstance(value, str) and value for value in arguments):
                raise ValueError("invalid startup command")
            command_line = subprocess.list2cmdline(arguments)
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, command_line)
        else:
            with suppress(FileNotFoundError):
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)


def start_with_windows_enabled() -> bool:
    if sys.platform != "win32":
        return False
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def wol_diagnostics() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []
    script = (
        "$adapters=Get-NetAdapter -Physical -ErrorAction SilentlyContinue;"
        "$adapters|ForEach-Object{[pscustomobject]@{name=$_.Name;description=$_.InterfaceDescription;"
        "status=[string]$_.Status;mac=$_.MacAddress;wakeOnMagicPacket=$null;wakePermission=$null}}"
        "|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
        shell=False,
    )
    if completed.returncode or not completed.stdout.strip():
        return []
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else [value]
