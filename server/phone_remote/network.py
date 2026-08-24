from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
import sys
import threading
import time
import winreg
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .subprocess_utils import hidden_window_kwargs

API_FIREWALL_RULE = "Phone Remote API"
DISCOVERY_FIREWALL_RULE = "Phone Remote Discovery"
STARTUP_VALUE_NAME = "Phone Remote"
PHYSICAL_ADDRESS_CACHE_SECONDS = 5 * 60.0
WAKE_TARGET_CACHE_SECONDS = 5 * 60.0

_physical_address_cache: tuple[str, ...] = ()
_physical_address_cached_at = float("-inf")
_physical_address_cache_lock = threading.Lock()


def local_ipv4_addresses() -> list[str]:
    if sys.platform == "win32":
        physical = [value for value in _windows_physical_ipv4_addresses() if _is_lan_ipv4(value)]
        if physical:
            return physical
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if _is_lan_ipv4(address) and address not in addresses:
                addresses.append(address)
    except socket.gaierror:
        pass
    return addresses


def _windows_physical_ipv4_addresses() -> tuple[str, ...]:
    global _physical_address_cache, _physical_address_cached_at

    now = time.monotonic()
    with _physical_address_cache_lock:
        if now - _physical_address_cached_at < PHYSICAL_ADDRESS_CACHE_SECONDS:
            return _physical_address_cache
        _physical_address_cache = _query_windows_physical_ipv4_addresses()
        _physical_address_cached_at = time.monotonic()
        return _physical_address_cache


def _query_windows_physical_ipv4_addresses() -> tuple[str, ...]:
    script = (
        "$items=Get-NetIPConfiguration -ErrorAction SilentlyContinue | "
        "Where-Object {$_.NetAdapter.Status -eq 'Up' -and $_.NetAdapter.HardwareInterface};"
        "$items|ForEach-Object{$_.IPv4Address|ForEach-Object{$_.IPAddress}}|"
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            shell=False,
            **hidden_window_kwargs(),
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode or not completed.stdout.strip():
        return ()
    try:
        value: Any = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return ()
    entries = value if isinstance(value, list) else [value]
    addresses: list[str] = []
    for item in entries:
        address = str(item)
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.version == 4 and address not in addresses:
            addresses.append(address)
    return tuple(addresses)


def _is_lan_ipv4(address: str) -> bool:
    try:
        value = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        return False
    return value.is_link_local or _is_rfc1918_ipv4(address)


def _is_rfc1918_ipv4(address: str) -> bool:
    try:
        value = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        return False
    return (
        value in ipaddress.IPv4Network("10.0.0.0/8")
        or value in ipaddress.IPv4Network("172.16.0.0/12")
        or value in ipaddress.IPv4Network("192.168.0.0/16")
    )


def is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def is_private_lan(address: str) -> bool:
    try:
        value = ipaddress.ip_address(address)
    except ValueError:
        return False
    return value.is_loopback or value.is_link_local or _is_rfc1918_ipv4(address)


@dataclass(frozen=True)
class NetworkProfile:
    name: str
    category: str
    ipv4_connectivity: str


class NetworkDiagnostics:
    def __init__(self) -> None:
        self._wake_targets_cache: list[dict[str, str]] = []
        self._wake_targets_cached_at: float | None = None
        self._wake_targets_cache_lock = threading.Lock()

    def addresses(self) -> list[str]:
        return local_ipv4_addresses()

    def refresh_runtime(self) -> None:
        """Warm expensive status data outside HTTP request threads."""
        self.addresses()
        self.wake_targets()

    def start_with_windows(self) -> bool:
        return start_with_windows_enabled()

    def wol_diagnostics(self) -> list[dict[str, Any]]:
        return wol_diagnostics()

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
            **hidden_window_kwargs(),
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
                command,
                capture_output=True,
                timeout=10,
                check=False,
                shell=False,
                **hidden_window_kwargs(),
            )
            result[key] = completed.returncode == 0
        return result

    def wake_targets(self) -> list[dict[str, str]]:
        if sys.platform != "win32":
            return []
        with self._wake_targets_cache_lock:
            now = time.monotonic()
            if (
                self._wake_targets_cached_at is not None
                and now - self._wake_targets_cached_at < WAKE_TARGET_CACHE_SECONDS
            ):
                return list(self._wake_targets_cache)
            script = (
                "$items=Get-NetIPConfiguration -ErrorAction SilentlyContinue | "
                "Where-Object {$_.NetAdapter.Status -eq 'Up' -and $_.NetAdapter.HardwareInterface};"
                "$items|ForEach-Object{$adapter=$_.NetAdapter;"
                "$_.IPv4Address|ForEach-Object{[pscustomobject]@{mac=$adapter.MacAddress;"
                "address=$_.IPAddress;prefixLength=$_.PrefixLength}}}|ConvertTo-Json -Compress"
            )
            try:
                completed = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    check=False,
                    shell=False,
                    **hidden_window_kwargs(),
                )
            except (OSError, subprocess.SubprocessError):
                self._wake_targets_cached_at = now
                return list(self._wake_targets_cache)
            if completed.returncode or not completed.stdout.strip():
                self._wake_targets_cached_at = now
                return list(self._wake_targets_cache)
            try:
                value: Any = json.loads(completed.stdout)
            except json.JSONDecodeError:
                self._wake_targets_cached_at = now
                return list(self._wake_targets_cache)
            entries = value if isinstance(value, list) else [value]
            targets: list[dict[str, str]] = []
            seen: set[tuple[str, str]] = set()
            for item in entries:
                if not isinstance(item, dict):
                    continue
                try:
                    address = ipaddress.IPv4Address(str(item.get("address", "")))
                    prefix_length = int(item.get("prefixLength", -1))
                    network = ipaddress.IPv4Network(f"{address}/{prefix_length}", strict=False)
                except (
                    ipaddress.AddressValueError,
                    ipaddress.NetmaskValueError,
                    TypeError,
                    ValueError,
                ):
                    continue
                raw_mac = "".join(
                    character for character in str(item.get("mac", "")) if character.isalnum()
                )
                if len(raw_mac) != 12 or any(
                    character not in "0123456789abcdefABCDEF" for character in raw_mac
                ):
                    continue
                mac = ":".join(raw_mac[index : index + 2] for index in range(0, 12, 2)).upper()
                key = (mac, str(address))
                if key in seen:
                    continue
                seen.add(key)
                targets.append(
                    {
                        "mac": mac,
                        "address": str(address),
                        "broadcast": str(network.broadcast_address),
                    }
                )
            self._wake_targets_cache = targets
            self._wake_targets_cached_at = now
            return list(targets)


def firewall_install_commands(
    executable: Path, port: int, web_port: int | None = None
) -> list[list[str]]:
    program = str(executable.resolve())
    tcp_ports = str(port) if web_port is None else f"{port},{web_port}"
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
            f"localport={tcp_ports}",
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
        **hidden_window_kwargs(),
    )
    if completed.returncode or not completed.stdout.strip():
        return []
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else [value]
