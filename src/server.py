import ctypes
from ctypes import wintypes
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSET_ROOT = ROOT / "assets"
RUNTIME_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("PHONE_REMOTE_CONFIG", str(RUNTIME_ROOT / "config.json")))
ICON_ROOT = RUNTIME_ROOT / "icons"
HOST = "0.0.0.0"
PORT = int(os.environ.get("SETTOP_REMOTE_PORT", "8765"))
MAX_REQUEST_BYTES = 16 * 1024
MAX_TEXT_LENGTH = 2000
ERROR_ALREADY_EXISTS = 183

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml; charset=utf-8",
    ".webp": "image/webp",
}

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

KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12
VK_F4 = 0x73
VK_LWIN = 0x5B
VK_D = 0x44
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


USER32 = ctypes.WinDLL("user32", use_last_error=True)
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
USER32.GetForegroundWindow.restype = wintypes.HWND
USER32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
USER32.GetWindowThreadProcessId.restype = wintypes.DWORD
USER32.GetGUIThreadInfo.argtypes = (wintypes.DWORD, ctypes.POINTER(GUITHREADINFO))
USER32.GetGUIThreadInfo.restype = wintypes.BOOL
USER32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
USER32.PostMessageW.restype = wintypes.BOOL
KERNEL32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
KERNEL32.CreateMutexW.restype = wintypes.HANDLE

APP_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
ICON_SUFFIXES = {".jpg", ".jpeg", ".png", ".svg", ".webp"}


def require_text(value, field, max_length=260):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError("invalid {}".format(field))
    return value.strip()


def require_arguments(value, field):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 32 or not all(isinstance(item, str) for item in value):
        raise ValueError("invalid {}".format(field))
    return list(value)


def require_absolute_path(value, field):
    path = require_text(value, field, 1024)
    if not Path(os.path.expandvars(path)).is_absolute():
        raise ValueError("{} must be an absolute path".format(field))
    return path


def validate_config(raw):
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("unsupported config version")

    browser_source = raw.get("browsers", {})
    if not isinstance(browser_source, dict):
        raise ValueError("browsers must be an object")
    browsers = {}
    for browser_id, value in browser_source.items():
        if not APP_ID_PATTERN.fullmatch(str(browser_id)) or not isinstance(value, dict):
            raise ValueError("invalid browser entry")
        browsers[browser_id] = {
            "path": require_absolute_path(value.get("path"), "browser path"),
            "args": require_arguments(value.get("args"), "browser args"),
            "fullscreenArgs": require_arguments(value.get("fullscreenArgs"), "browser fullscreenArgs"),
        }

    app_source = raw.get("apps")
    if not isinstance(app_source, list):
        raise ValueError("apps must be an array")
    apps = []
    app_ids = set()
    for value in app_source:
        if not isinstance(value, dict):
            raise ValueError("invalid app entry")
        app_id = require_text(value.get("id"), "app id", 32)
        if not APP_ID_PATTERN.fullmatch(app_id) or app_id in app_ids:
            raise ValueError("invalid or duplicate app id: {}".format(app_id))
        app_ids.add(app_id)

        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false")
        icon = require_text(value.get("icon"), "app icon", 128)
        if Path(icon).name != icon or Path(icon).suffix.lower() not in ICON_SUFFIXES:
            raise ValueError("invalid app icon: {}".format(icon))

        launch_source = value.get("launch")
        if not isinstance(launch_source, dict):
            raise ValueError("invalid launch settings: {}".format(app_id))
        launch_type = launch_source.get("type")
        if launch_type == "program":
            launch = {
                "type": "program",
                "path": require_absolute_path(launch_source.get("path"), "program path"),
                "args": require_arguments(launch_source.get("args"), "program args"),
            }
        elif launch_type == "browser":
            browser_id = require_text(launch_source.get("browser"), "browser id", 32)
            if browser_id not in browsers:
                raise ValueError("unknown browser: {}".format(browser_id))
            url = launch_source.get("url", "")
            if not isinstance(url, str) or len(url) > 2048:
                raise ValueError("invalid browser URL")
            if url and urlparse(url).scheme.lower() not in ("http", "https"):
                raise ValueError("browser URL must use http or https")
            fullscreen = launch_source.get("fullscreen", False)
            if not isinstance(fullscreen, bool):
                raise ValueError("fullscreen must be true or false")
            launch = {
                "type": "browser",
                "browser": browser_id,
                "url": url,
                "fullscreen": fullscreen,
            }
        else:
            raise ValueError("unknown launch type: {}".format(launch_type))

        apps.append({
            "id": app_id,
            "name": require_text(value.get("name"), "app name", 40),
            "enabled": enabled,
            "icon": icon,
            "launch": launch,
        })

    return {"version": 1, "browsers": browsers, "apps": apps}


class ConfigStore:
    def __init__(self, path):
        self.path = path
        self._lock = threading.RLock()
        self._signature = None
        self._config = None
        self._error = None

    def _file_signature(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return "missing", str(self.path)

    def get(self):
        with self._lock:
            signature = self._file_signature()
            if signature == self._signature and self._config is not None:
                return self._config
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
                config = validate_config(raw)
            except Exception as exc:
                self._signature = signature
                self._error = str(exc)
                if self._config is None:
                    raise ValueError("config error: {}".format(exc))
                return self._config
            self._signature = signature
            self._config = config
            self._error = None
            return config

    @property
    def error(self):
        self.get()
        return self._error

    def public_apps(self):
        apps = []
        for app in self.get()["apps"]:
            if not app["enabled"]:
                continue
            icon_path = ICON_ROOT / app["icon"]
            try:
                icon_version = icon_path.stat().st_mtime_ns
            except OSError:
                icon_version = 0
            apps.append({
                "id": app["id"],
                "name": app["name"],
                "icon": "/app-icons/{}?v={}".format(quote(app["icon"], safe=""), icon_version),
            })
        return apps

    def launch_args(self, app_id):
        config = self.get()
        app = next((item for item in config["apps"] if item["enabled"] and item["id"] == app_id), None)
        if app is None:
            raise ValueError("unknown app")
        launch = app["launch"]
        if launch["type"] == "program":
            return [os.path.expandvars(launch["path"])] + launch["args"]
        browser = config["browsers"][launch["browser"]]
        args = [os.path.expandvars(browser["path"])] + browser["args"]
        if launch["fullscreen"]:
            args.extend(browser["fullscreenArgs"])
        if launch["url"]:
            args.append(launch["url"])
        return args


CONFIG = ConfigStore(CONFIG_PATH)


def key(vk_code):
    USER32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.025)
    USER32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def key_combo(*vk_codes):
    for vk_code in vk_codes:
        USER32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.04)
    for vk_code in reversed(vk_codes):
        USER32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def send_text(text):
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError("text is too long")

    foreground = USER32.GetForegroundWindow()
    if not foreground:
        raise OSError("no active window")

    thread_id = USER32.GetWindowThreadProcessId(foreground, None)
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if not USER32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
        raise ctypes.WinError()
    target = info.hwndFocus or info.hwndActive or foreground

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    encoded = normalized.encode("utf-16-le")
    for index in range(0, len(encoded), 2):
        code_unit = int.from_bytes(encoded[index:index + 2], "little")
        if code_unit == 0x000A:
            code_unit = 0x000D
        if not USER32.PostMessageW(target, WM_CHAR, code_unit, 1):
            raise OSError("keyboard input failed")
        if index and index % 128 == 0:
            time.sleep(0.005)


def mouse_move(dx, dy):
    USER32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)


def mouse_click(button="left"):
    if button == "right":
        USER32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.025)
        USER32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        return
    USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.025)
    USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def mouse_wheel(delta):
    USER32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)


def start_process(args, cwd=None):
    exe = Path(args[0])
    if not exe.exists():
        raise FileNotFoundError(str(exe))
    subprocess.Popen(args, cwd=str(cwd or exe.parent), close_fds=True)


def local_addresses():
    addresses = []
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127.") and address not in addresses:
                addresses.append(address)
    except socket.gaierror:
        pass
    return addresses


def perform(action):
    if action == "desktop":
        key_combo(VK_LWIN, VK_D)
        return {"ok": True, "message": "desktop"}
    if action.startswith("app:"):
        app_id = action.split(":", 1)[1]
        start_process(CONFIG.launch_args(app_id))
        return {"ok": True, "message": app_id}
    if action == "close_active":
        key_combo(VK_MENU, VK_F4)
        return {"ok": True, "message": "closed active window"}
    if action in VK:
        key(VK[action])
        return {"ok": True, "message": action}
    if action == "sleep":
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return {"ok": True, "message": "sleep"}
    if action == "restart":
        subprocess.Popen(["shutdown.exe", "/r", "/t", "0"])
        return {"ok": True, "message": "restart"}
    if action == "shutdown":
        subprocess.Popen(["shutdown.exe", "/s", "/t", "0"])
        return {"ok": True, "message": "shutdown"}
    raise ValueError("unknown action")


def perform_mouse(data):
    kind = str(data.get("type", ""))
    if kind == "move":
        dx = max(-120, min(120, float(data.get("dx", 0))))
        dy = max(-120, min(120, float(data.get("dy", 0))))
        mouse_move(dx, dy)
        return {"ok": True, "message": "move"}
    if kind == "click":
        mouse_click(str(data.get("button", "left")))
        return {"ok": True, "message": "click"}
    if kind == "double":
        mouse_click("left")
        time.sleep(0.06)
        mouse_click("left")
        return {"ok": True, "message": "double"}
    if kind == "wheel":
        delta = max(-480, min(480, int(data.get("delta", 0))))
        mouse_wheel(delta)
        return {"ok": True, "message": "wheel"}
    raise ValueError("unknown mouse event")


class Handler(BaseHTTPRequestHandler):
    server_version = "PhoneRemote/2.1"

    def log_message(self, fmt, *args):
        return

    def send_payload(self, status, payload, content_type, cache_control="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache_control)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_payload(status, payload, "application/json; charset=utf-8")

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise ValueError("request is too large")
        body = self.rfile.read(length) if length else b"{}"
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be an object")
        return data

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            payload = (ROOT / "index.html").read_bytes()
            self.send_payload(200, payload, "text/html; charset=utf-8")
            return
        if path.startswith("/assets/"):
            name = Path(path).name
            asset = ASSET_ROOT / name
            content_type = CONTENT_TYPES.get(asset.suffix.lower())
            if asset.is_file() and content_type:
                payload = asset.read_bytes()
                self.send_payload(200, payload, content_type, "public, max-age=86400")
                return
        if path.startswith("/app-icons/"):
            name = unquote(path[len("/app-icons/"):])
            icon = ICON_ROOT / name
            content_type = CONTENT_TYPES.get(icon.suffix.lower())
            if Path(name).name == name and icon.is_file() and content_type:
                self.send_payload(200, icon.read_bytes(), content_type, "public, max-age=86400")
                return
        if path == "/api/apps":
            try:
                apps = CONFIG.public_apps()
                self.send_json(200, {"ok": True, "apps": apps, "warning": CONFIG.error})
            except Exception as exc:
                self.send_json(500, {"ok": False, "apps": [], "error": str(exc)})
            return
        if path == "/api/status":
            try:
                CONFIG.get()
                config_error = CONFIG.error
            except Exception as exc:
                config_error = str(exc)
            self.send_json(200, {
                "ok": True,
                "version": "2.1",
                "addresses": local_addresses(),
                "port": PORT,
                "configOk": config_error is None,
                "configError": config_error,
            })
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/action", "/api/mouse", "/api/text"):
            self.send_error(404)
            return
        try:
            data = self.read_json()
            if path == "/api/mouse":
                result = perform_mouse(data)
            elif path == "/api/text":
                value = data.get("text", "")
                if not isinstance(value, str):
                    raise ValueError("text must be a string")
                send_text(value)
                result = {"ok": True, "message": "text"}
            else:
                result = perform(str(data.get("action", "")))
            self.send_json(200, result)
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})


class RemoteServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def acquire_single_instance():
    handle = KERNEL32.CreateMutexW(None, False, "Local\\PhoneRemote-{}".format(PORT))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def main():
    mutex = acquire_single_instance()
    if mutex is None:
        return
    os.chdir(str(ROOT))
    server = RemoteServer((HOST, PORT), Handler)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        KERNEL32.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
