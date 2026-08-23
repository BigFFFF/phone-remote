from __future__ import annotations

import base64
import ctypes
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from typing import Any, Protocol

from .app_launcher import AppLauncher
from .subprocess_utils import hidden_window_kwargs

MAX_TEXT_LENGTH = 2000
MAX_MOUSE_MOVE = 120.0
MAX_WHEEL_DELTA = 480

VK = {
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "enter": 0x0D,
    "tab": 0x09,
    "back": 0x08,
    "escape": 0x1B,
    "space": 0x20,
    "f11": 0x7A,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
    "media_play_pause": 0xB3,
    "media_next": 0xB0,
    "media_previous": 0xB1,
}

VK_MENU = 0x12
VK_F4 = 0x73
VK_LWIN = 0x5B
VK_D = 0x44


class ControlBackend(Protocol):
    def key(self, vk_code: int) -> None: ...

    def key_combo(self, *vk_codes: int) -> None: ...

    def text(self, value: str) -> None: ...

    def mouse_move(self, dx: float, dy: float) -> None: ...

    def mouse_click(self, button: str) -> None: ...

    def mouse_wheel(self, delta: int) -> None: ...

    def power(self, action: str) -> None: ...


class WindowsBackend:
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_WHEEL = 0x0800
    WM_CHAR = 0x0102

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND),
            ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND),
            ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND),
            ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Windows control is only available on Windows")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        )
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetGUIThreadInfo.argtypes = (
            wintypes.DWORD,
            ctypes.POINTER(self.GUITHREADINFO),
        )
        self.user32.GetGUIThreadInfo.restype = wintypes.BOOL
        self.user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self.user32.PostMessageW.restype = wintypes.BOOL
        self._mouse_remainder_x = 0.0
        self._mouse_remainder_y = 0.0

    def key(self, vk_code: int) -> None:
        self.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.025)
        self.user32.keybd_event(vk_code, 0, self.KEYEVENTF_KEYUP, 0)

    def key_combo(self, *vk_codes: int) -> None:
        for vk_code in vk_codes:
            self.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.04)
        for vk_code in reversed(vk_codes):
            self.user32.keybd_event(vk_code, 0, self.KEYEVENTF_KEYUP, 0)

    def text(self, value: str) -> None:
        foreground = self.user32.GetForegroundWindow()
        if not foreground:
            raise OSError("no active window")
        thread_id = self.user32.GetWindowThreadProcessId(foreground, None)
        info = self.GUITHREADINFO(cbSize=ctypes.sizeof(self.GUITHREADINFO))
        if not self.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            raise ctypes.WinError()
        target = info.hwndFocus or info.hwndActive or foreground
        encoded = value.replace("\r\n", "\n").replace("\r", "\n").encode("utf-16-le")
        for index in range(0, len(encoded), 2):
            code_unit = int.from_bytes(encoded[index : index + 2], "little")
            if code_unit == 0x000A:
                code_unit = 0x000D
            if not self.user32.PostMessageW(target, self.WM_CHAR, code_unit, 1):
                raise OSError("keyboard input failed")
            if index and index % 128 == 0:
                time.sleep(0.005)

    def mouse_move(self, dx: float, dy: float) -> None:
        total_x = dx + self._mouse_remainder_x
        total_y = dy + self._mouse_remainder_y
        whole_x = int(total_x)
        whole_y = int(total_y)
        self._mouse_remainder_x = total_x - whole_x
        self._mouse_remainder_y = total_y - whole_y
        if whole_x != 0 or whole_y != 0:
            self.user32.mouse_event(self.MOUSEEVENTF_MOVE, whole_x, whole_y, 0, 0)

    def mouse_click(self, button: str) -> None:
        if button == "right":
            down, up = self.MOUSEEVENTF_RIGHTDOWN, self.MOUSEEVENTF_RIGHTUP
        else:
            down, up = self.MOUSEEVENTF_LEFTDOWN, self.MOUSEEVENTF_LEFTUP
        self.user32.mouse_event(down, 0, 0, 0, 0)
        time.sleep(0.025)
        self.user32.mouse_event(up, 0, 0, 0, 0)

    def mouse_wheel(self, delta: int) -> None:
        self.user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)

    def power(self, action: str) -> None:
        commands = {
            "sleep": _windows_sleep_command(),
            "hibernate": ["shutdown.exe", "/h"],
            "restart": ["shutdown.exe", "/r", "/t", "0"],
            "shutdown": ["shutdown.exe", "/s", "/t", "0"],
        }
        subprocess.Popen(
            commands[action],
            close_fds=True,
            shell=False,
            **hidden_window_kwargs(),
        )


def _windows_sleep_command() -> list[str]:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$ok=[System.Windows.Forms.Application]::SetSuspendState("
        "[System.Windows.Forms.PowerState]::Suspend,$false,$false);"
        "if(-not $ok){exit 1}"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded,
    ]


class ControlService:
    def __init__(self, backend: ControlBackend, launcher: AppLauncher):
        self.backend = backend
        self.launcher = launcher
        self._lock = threading.RLock()

    def action(self, action: Any) -> dict[str, Any]:
        if not isinstance(action, str) or len(action) > 80:
            raise ValueError("invalid action")
        with self._lock:
            if action == "desktop":
                self.backend.key_combo(VK_LWIN, VK_D)
            elif action == "close_active":
                self.backend.key_combo(VK_MENU, VK_F4)
            elif action in VK:
                self.backend.key(VK[action])
            else:
                raise ValueError("unknown action")
        return {"ok": True, "message": action}

    def launch_app(self, app_id: Any) -> dict[str, Any]:
        if not isinstance(app_id, str) or not app_id or len(app_id) > 32:
            raise ValueError("invalid app id")
        with self._lock:
            self.launcher.launch(app_id)
        return {"ok": True, "message": app_id}

    def mouse(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("mouse body must be an object")
        kind = data.get("type")
        with self._lock:
            if kind == "move":
                dx = _clamp_float(data.get("dx", 0), -MAX_MOUSE_MOVE, MAX_MOUSE_MOVE)
                dy = _clamp_float(data.get("dy", 0), -MAX_MOUSE_MOVE, MAX_MOUSE_MOVE)
                self.backend.mouse_move(dx, dy)
            elif kind == "click":
                button = data.get("button", "left")
                if button not in {"left", "right"}:
                    raise ValueError("invalid mouse button")
                self.backend.mouse_click(button)
            elif kind == "double":
                self.backend.mouse_click("left")
                time.sleep(0.06)
                self.backend.mouse_click("left")
            elif kind == "wheel":
                delta = int(_clamp_float(data.get("delta", 0), -MAX_WHEEL_DELTA, MAX_WHEEL_DELTA))
                self.backend.mouse_wheel(delta)
            else:
                raise ValueError("unknown mouse event")
        return {"ok": True, "message": str(kind)}

    def text(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, str):
            raise ValueError("text must be a string")
        if len(value) > MAX_TEXT_LENGTH:
            raise ValueError("text is too long")
        with self._lock:
            self.backend.text(value)
        return {"ok": True, "message": "text"}

    def power(self, action: Any) -> dict[str, Any]:
        if action not in {"sleep", "hibernate", "restart", "shutdown"}:
            raise ValueError("unknown power action")
        with self._lock:
            self.backend.power(action)
        return {"ok": True, "message": str(action)}


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid numeric value") from exc
    if number != number or number in {float("inf"), float("-inf")}:
        raise ValueError("invalid numeric value")
    return max(minimum, min(maximum, number))
