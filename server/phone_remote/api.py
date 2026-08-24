from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import secrets
import socketserver
import ssl
import threading
from contextlib import suppress
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import API_VERSION, __version__
from .auth import CredentialStore
from .catalog import ApplicationCatalog
from .config import ConfigStore
from .localization import UiLanguageStore
from .network import (
    NetworkDiagnostics,
    is_loopback,
    is_private_lan,
    set_start_with_windows,
)
from .pairing import PairingError, PairingManager, PairingRateLimited
from .paths import RuntimePaths
from .security import ServerIdentity
from .windows_control import ControlService

MAX_REQUEST_BYTES = 16 * 1024
MAX_WEBSOCKET_FRAME_BYTES = 4 * 1024
MAX_CONCURRENT_CONNECTIONS = 64
MAX_REQUESTS_PER_CONNECTION = 100
HTTP_IDLE_TIMEOUT_SECONDS = 30.0
TLS_HANDSHAKE_TIMEOUT_SECONDS = 5.0
NETWORK_PROFILE_REFRESH_SECONDS = 60
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
REPEATABLE_ACTIONS = {
    "up",
    "down",
    "left",
    "right",
    "volume_up",
    "volume_down",
}
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml; charset=utf-8",
    ".webp": "image/webp",
}


def _signaled_event() -> threading.Event:
    event = threading.Event()
    event.set()
    return event


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class WebSocketProtocolError(Exception):
    pass


@dataclass
class ApiContext:
    identity: ServerIdentity
    paths: RuntimePaths
    config: ConfigStore
    credentials: CredentialStore
    pairing: PairingManager
    control: ControlService
    catalog: ApplicationCatalog
    network: NetworkDiagnostics
    logger: logging.Logger
    port: int
    web_port: int | None = None
    startup_command: tuple[str, ...] = ()
    ui_language: UiLanguageStore | None = None
    admin_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    catalog_ready: threading.Event = field(default_factory=_signaled_event)
    _profile_lock: threading.Lock = field(default_factory=threading.Lock)
    _profile_stop: threading.Event = field(default_factory=threading.Event)
    _profile_thread: threading.Thread | None = None
    _public_only: bool = True

    def start_network_monitor(self) -> None:
        with self._profile_lock:
            if self._profile_thread is not None:
                return
        thread = threading.Thread(
            target=self._monitor_network_profile,
            name="phone-remote-network-profile",
            daemon=True,
        )
        with self._profile_lock:
            if self._profile_thread is not None:
                return
            self._profile_stop.clear()
            self._profile_thread = thread
        thread.start()

    def stop_network_monitor(self) -> None:
        with self._profile_lock:
            thread = self._profile_thread
            self._profile_thread = None
            self._profile_stop.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _monitor_network_profile(self) -> None:
        while not self._profile_stop.is_set():
            self._refresh_network_profile()
            refresh_runtime = getattr(self.network, "refresh_runtime", None)
            if refresh_runtime is not None:
                try:
                    refresh_runtime()
                except Exception:
                    self.logger.exception("network runtime refresh failed")
            if self._profile_stop.wait(NETWORK_PROFILE_REFRESH_SECONDS):
                return

    def _refresh_network_profile(self) -> None:
        try:
            public_only = self.network.public_only()
        except Exception:
            self.logger.exception("network profile refresh failed")
            return
        with self._profile_lock:
            self._public_only = public_only

    def remote_allowed(self, address: str) -> bool:
        if is_loopback(address):
            return True
        with self._profile_lock:
            return not self._public_only


class PhoneRemoteServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        context: ApiContext,
        *,
        allow_management: bool = True,
        private_lan_only: bool = False,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int = MAX_CONCURRENT_CONNECTIONS,
        request_timeout_seconds: float = HTTP_IDLE_TIMEOUT_SECONDS,
        tls_handshake_timeout_seconds: float = TLS_HANDSHAKE_TIMEOUT_SECONDS,
    ):
        if max_connections < 1:
            raise ValueError("max_connections must be positive")
        if request_timeout_seconds <= 0 or tls_handshake_timeout_seconds <= 0:
            raise ValueError("connection timeouts must be positive")
        super().__init__(address, PhoneRemoteHandler)
        self.context = context
        self.allow_management = allow_management
        self.private_lan_only = private_lan_only
        self.ssl_context = ssl_context
        self.request_timeout_seconds = request_timeout_seconds
        self.tls_handshake_timeout_seconds = tls_handshake_timeout_seconds
        self._connection_slots = threading.BoundedSemaphore(max_connections)

    def server_bind(self) -> None:
        # HTTPServer.server_bind performs a reverse-DNS lookup for the bind
        # address. That lookup can block for many seconds on Windows when the
        # server listens on 0.0.0.0, and this process creates two listeners.
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)

    def process_request(self, request: Any, client_address: Any) -> None:
        if not self._connection_slots.acquire(blocking=False):
            self.context.logger.warning("connection limit reached client=%s", client_address[0])
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._connection_slots.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        active_request = request
        try:
            if self.ssl_context is not None:
                request.settimeout(self.tls_handshake_timeout_seconds)
                active_request = self.ssl_context.wrap_socket(
                    request,
                    server_side=True,
                    do_handshake_on_connect=False,
                )
                active_request.do_handshake()
            active_request.settimeout(self.request_timeout_seconds)
            self.finish_request(active_request, client_address)
        except (TimeoutError, ssl.SSLError, ConnectionError) as exc:
            self.context.logger.debug(
                "connection closed client=%s reason=%s", client_address[0], exc
            )
        except Exception:
            self.handle_error(active_request, client_address)
        finally:
            self.shutdown_request(active_request)
            self._connection_slots.release()


class PhoneRemoteHandler(BaseHTTPRequestHandler):
    server: PhoneRemoteServer
    server_version = "PhoneRemote/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def handle(self) -> None:
        self.close_connection = True
        for _ in range(MAX_REQUESTS_PER_CONNECTION):
            self.handle_one_request()
            if self.close_connection:
                return
        self.close_connection = True

    def log_message(self, format_string: str, *args: Any) -> None:
        self.server.context.logger.debug(
            "http client=%s message=%s", self.client_address[0], format_string % args
        )

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def do_HEAD(self) -> None:
        self._handle("HEAD")

    def do_OPTIONS(self) -> None:
        self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"ok": False, "error": "method not allowed"})

    def _handle(self, method: str) -> None:
        context = self.server.context
        try:
            if self.server.private_lan_only and not is_private_lan(self.client_address[0]):
                raise ApiError(HTTPStatus.FORBIDDEN, "Web Remote is limited to the private LAN")
            if not context.remote_allowed(self.client_address[0]):
                raise ApiError(HTTPStatus.FORBIDDEN, "connections are blocked on Public networks")
            path = urlparse(self.path).path
            if method == "GET" and path == "/api/v1/pointer":
                self._handle_pointer_websocket()
                return
            if method in {"GET", "HEAD"} and self._serve_static(path, head=method == "HEAD"):
                return
            if path.startswith("/api/v1/admin/"):
                if not self.server.allow_management:
                    raise ApiError(HTTPStatus.FORBIDDEN, "management API is unavailable here")
                self._require_admin()
                payload = self._admin_route(method, path)
                self._json(HTTPStatus.OK, payload, head=method == "HEAD")
                return
            payload, status = self._api_route(method, path)
            self._json(status, payload, head=method == "HEAD")
        except ApiError as exc:
            self._json(exc.status, {"ok": False, "error": exc.message})
        except PairingRateLimited as exc:
            context.logger.warning("pairing rate limited source=%s", self.client_address[0])
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"ok": False, "error": str(exc)})
        except PairingError as exc:
            context.logger.warning(
                "pairing failed source=%s reason=%s", self.client_address[0], exc
            )
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except (ValueError, FileNotFoundError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except TimeoutError:
            self.close_connection = True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True
        except Exception:
            context.logger.exception("request failed method=%s path=%s", method, self.path)
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "internal server error"},
            )

    def _api_route(self, method: str, path: str) -> tuple[dict[str, Any], int]:
        context = self.server.context
        if method == "GET" and path == "/api/v1/info":
            return (
                {
                    "ok": True,
                    "serverId": context.identity.server_id,
                    "name": context.identity.display_name,
                    "version": __version__,
                    "apiVersion": API_VERSION,
                    "pairing": context.pairing.active() is not None,
                    "identityFingerprint": context.identity.fingerprint,
                    "certificateFingerprint": context.identity.certificate_fingerprint,
                },
                HTTPStatus.OK,
            )
        if method == "POST" and path == "/api/v1/pair/request":
            _validate_body_keys(self._read_json(), required=set(), allowed=set())
            session = context.pairing.start(self.client_address[0])
            return (
                {
                    "ok": True,
                    "sessionId": session.session_id,
                    "expiresIn": session.expires_in,
                },
                HTTPStatus.CREATED,
            )
        if method == "POST" and path == "/api/v1/pair/complete":
            data = self._read_json()
            _validate_body_keys(
                data,
                required={"sessionId", "code", "deviceName", "platform"},
                allowed={"sessionId", "code", "deviceName", "platform"},
            )
            issued = context.pairing.complete(
                _body_text(data, "sessionId", 80),
                _body_text(data, "code", 6),
                _body_text(data, "deviceName", 120),
                _body_text(data, "platform", 40),
            )
            context.logger.info("pairing succeeded client=%s", issued.client_id)
            return (
                {
                    "ok": True,
                    "clientId": issued.client_id,
                    "credential": issued.credential,
                    "serverId": context.identity.server_id,
                    "identityFingerprint": context.identity.fingerprint,
                },
                HTTPStatus.CREATED,
            )

        client = self._require_client()
        client_id = str(client["client_id"])
        if method == "GET" and path == "/api/v1/status":
            config_error = None
            try:
                context.config.get()
                config_error = context.config.error
            except ValueError as exc:
                config_error = str(exc)
            return (
                {
                    "ok": True,
                    "serverId": context.identity.server_id,
                    "name": context.identity.display_name,
                    "version": __version__,
                    "apiVersion": API_VERSION,
                    "addresses": context.network.addresses(),
                    "wakeTargets": context.network.wake_targets(),
                    "port": context.port,
                    "webPort": context.web_port,
                    "configOk": config_error is None,
                    "configError": config_error,
                },
                HTTPStatus.OK,
            )
        if method == "GET" and path == "/api/v1/apps":
            context.catalog_ready.wait(timeout=10)
            try:
                apps = context.config.public_apps()
                warning = context.config.error
            except ValueError as exc:
                apps, warning = [], str(exc)
            return {"ok": True, "apps": apps, "warning": warning}, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/action":
            data = self._read_json()
            _validate_body_keys(data, required={"action"}, allowed={"action"})
            action = data.get("action")
            result = context.control.action(action)
            log = context.logger.debug if action in REPEATABLE_ACTIONS else context.logger.info
            log("control action client=%s action=%s", client_id, action)
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/mouse":
            result = context.control.mouse(_validate_mouse_body(self._read_json()))
            log = context.logger.debug if result["message"] == "move" else context.logger.info
            log("control action client=%s action=mouse:%s", client_id, result["message"])
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/text":
            data = self._read_json()
            _validate_body_keys(data, required={"text"}, allowed={"text"})
            result = context.control.text(data.get("text"))
            context.logger.info("control action client=%s action=text", client_id)
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/power":
            data = self._read_json()
            _validate_body_keys(data, required={"action"}, allowed={"action"})
            action = data.get("action")
            result = context.control.power(action)
            context.logger.info("control action client=%s action=power:%s", client_id, action)
            return result, HTTPStatus.OK
        if method == "POST" and path.startswith("/api/v1/apps/") and path.endswith("/launch"):
            _validate_body_keys(self._read_json(), required=set(), allowed=set())
            app_id = unquote(path[len("/api/v1/apps/") : -len("/launch")]).strip("/")
            result = context.control.launch_app(app_id)
            context.logger.info("control action client=%s action=app:%s", client_id, app_id)
            return result, HTTPStatus.OK
        raise ApiError(HTTPStatus.NOT_FOUND, "not found")

    def _admin_route(self, method: str, path: str) -> dict[str, Any]:
        context = self.server.context
        if method == "GET" and path == "/api/v1/admin/overview":
            return {
                "ok": True,
                "server": {
                    "serverId": context.identity.server_id,
                    "name": context.identity.display_name,
                    "version": __version__,
                    "apiVersion": API_VERSION,
                    "port": context.port,
                    "webPort": context.web_port,
                    "addresses": context.network.addresses(),
                    "identityFingerprint": context.identity.fingerprint,
                },
                "networkProfiles": [item.__dict__ for item in context.network.profiles()],
                "firewall": context.network.firewall_status(),
                "startWithWindows": context.network.start_with_windows(),
                "uiLanguage": context.ui_language.get() if context.ui_language else "en",
                "wol": context.network.wol_diagnostics(),
                "clients": context.credentials.list_clients(),
                "apps": context.config.get()["apps"],
            }
        if method == "GET" and path == "/api/v1/admin/pair":
            session = context.pairing.active(reveal_code=True)
            if session is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "no active pairing request")
            return {
                "ok": True,
                "sessionId": session.session_id,
                "code": session.code,
                "expiresIn": session.expires_in,
            }
        if method == "GET" and path == "/api/v1/admin/clients":
            return {"ok": True, "clients": context.credentials.list_clients()}
        if method == "POST" and path == "/api/v1/admin/runtime/startup":
            data = self._read_json()
            _validate_body_keys(data, required={"enabled"}, allowed={"enabled"})
            enabled = data.get("enabled")
            if not isinstance(enabled, bool):
                raise ValueError("enabled must be true or false")
            if not context.startup_command:
                raise ValueError("startup command is unavailable")
            set_start_with_windows(context.startup_command, enabled)
            return {"ok": True, "enabled": enabled}
        if method == "POST" and path == "/api/v1/admin/runtime/language":
            data = self._read_json()
            _validate_body_keys(data, required={"language"}, allowed={"language"})
            if context.ui_language is None:
                raise ValueError("UI language preference is unavailable")
            return {"ok": True, "language": context.ui_language.set(data.get("language"))}
        if method == "POST" and path == "/api/v1/admin/clients/revoke-all":
            _validate_body_keys(self._read_json(), required=set(), allowed=set())
            return {"ok": True, "revoked": context.credentials.revoke_all()}
        if method == "DELETE" and path.startswith("/api/v1/admin/clients/"):
            client_id = unquote(path.rsplit("/", 1)[1])
            if not context.credentials.revoke(client_id):
                raise ApiError(HTTPStatus.NOT_FOUND, "client not found")
            return {"ok": True}
        if method == "POST" and path == "/api/v1/admin/apps/rescan":
            _validate_body_keys(self._read_json(), required=set(), allowed=set())
            return {"ok": True, "candidates": context.catalog.rescan()}
        if method == "POST" and path == "/api/v1/admin/apps/approve":
            data = self._read_json()
            _validate_body_keys(data, required={"discoveryId"}, allowed={"discoveryId"})
            return {"ok": True, "app": context.catalog.approve(_body_text(data, "discoveryId", 80))}
        if method == "POST" and path == "/api/v1/admin/apps/manual-program":
            data = self._read_json()
            _validate_body_keys(
                data,
                required={"name", "path"},
                allowed={"name", "path", "arguments"},
            )
            return {
                "ok": True,
                "app": context.catalog.add_program(
                    _body_text(data, "name", 80),
                    _body_text(data, "path", 1024),
                    data.get("arguments", []),
                ),
            }
        if method == "POST" and path == "/api/v1/admin/apps/manual-website":
            data = self._read_json()
            _validate_body_keys(
                data,
                required={"name", "browser", "url"},
                allowed={"name", "browser", "url", "fullscreen"},
            )
            return {
                "ok": True,
                "app": context.catalog.add_website(
                    _body_text(data, "name", 80),
                    _body_text(data, "browser", 32),
                    _body_text(data, "url", 2048),
                    fullscreen=data.get("fullscreen") is True,
                ),
            }
        if method == "POST" and path.startswith("/api/v1/admin/apps/"):
            app_id = unquote(path.rsplit("/", 1)[1])
            data = self._read_json()
            _validate_body_keys(data, required={"enabled"}, allowed={"enabled"})
            return {
                "ok": True,
                "app": context.catalog.set_enabled(app_id, data.get("enabled")),
            }
        if method == "DELETE" and path.startswith("/api/v1/admin/apps/"):
            app_id = unquote(path.rsplit("/", 1)[1])
            if not context.catalog.remove(app_id):
                raise ApiError(HTTPStatus.NOT_FOUND, "app not found")
            return {"ok": True}
        raise ApiError(HTTPStatus.NOT_FOUND, "not found")

    def _require_client(self) -> dict[str, Any]:
        value = self.headers.get("Authorization", "")
        prefix = "Bearer "
        credential = value[len(prefix) :] if value.startswith(prefix) else ""
        if not credential:
            protocols = {
                item.strip() for item in self.headers.get("Sec-WebSocket-Protocol", "").split(",")
            }
            credential = next(
                (item[len("auth.") :] for item in protocols if item.startswith("auth.")),
                "",
            )
        if not credential:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "authentication required")
        client = self.server.context.credentials.authenticate(credential)
        if client is None:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "invalid or revoked credential")
        return client

    def _handle_pointer_websocket(self) -> None:
        if self.headers.get("Upgrade", "").lower() != "websocket":
            raise ApiError(HTTPStatus.UPGRADE_REQUIRED, "websocket upgrade required")
        connection_tokens = {
            item.strip().lower() for item in self.headers.get("Connection", "").split(",")
        }
        if "upgrade" not in connection_tokens:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid websocket connection header")
        if self.headers.get("Sec-WebSocket-Version") != "13":
            raise ApiError(HTTPStatus.BAD_REQUEST, "unsupported websocket version")
        key = self.headers.get("Sec-WebSocket-Key", "")
        try:
            decoded_key = base64.b64decode(key, validate=True)
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid websocket key") from exc
        if len(decoded_key) != 16:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid websocket key")

        client = self._require_client()
        accept = base64.b64encode(hashlib.sha1(f"{key}{WEBSOCKET_GUID}".encode()).digest()).decode()
        self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        protocols = {
            item.strip() for item in self.headers.get("Sec-WebSocket-Protocol", "").split(",")
        }
        if "phone-remote.v1" in protocols:
            self.send_header("Sec-WebSocket-Protocol", "phone-remote.v1")
        self.end_headers()
        self.close_connection = True
        self.server.context.logger.debug(
            "pointer websocket connected client=%s", client["client_id"]
        )

        try:
            self._pointer_websocket_loop()
        except (ConnectionError, EOFError, OSError):
            pass
        except WebSocketProtocolError:
            self._send_websocket_close(1002)
        finally:
            self.server.context.logger.debug(
                "pointer websocket disconnected client=%s", client["client_id"]
            )

    def _pointer_websocket_loop(self) -> None:
        while True:
            opcode, payload = self._read_websocket_frame()
            if opcode == 0x8:
                self._send_websocket_frame(0x8, payload[:125])
                return
            if opcode == 0x9:
                self._send_websocket_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode != 0x1:
                raise WebSocketProtocolError("only text frames are supported")
            try:
                data = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise WebSocketProtocolError("invalid pointer frame") from exc
            if not isinstance(data, dict) or data.get("type") not in {"move", "wheel"}:
                raise WebSocketProtocolError("invalid pointer event")
            try:
                self.server.context.control.mouse(_validate_mouse_body(data))
            except ValueError as exc:
                raise WebSocketProtocolError("invalid pointer event") from exc

    def _read_websocket_frame(self) -> tuple[int, bytes]:
        header = self._read_exact(2)
        first, second = header
        if first & 0x70 or not first & 0x80:
            raise WebSocketProtocolError("fragmented websocket frames are unsupported")
        opcode = first & 0x0F
        if not second & 0x80:
            raise WebSocketProtocolError("client websocket frames must be masked")
        length = second & 0x7F
        if length == 126:
            length = int.from_bytes(self._read_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._read_exact(8), "big")
        if opcode & 0x08 and length > 125:
            raise WebSocketProtocolError("invalid websocket control frame")
        if length > MAX_WEBSOCKET_FRAME_BYTES:
            raise WebSocketProtocolError("websocket frame is too large")
        mask = self._read_exact(4)
        payload = self._read_exact(length)
        return opcode, bytes(value ^ mask[index % 4] for index, value in enumerate(payload))

    def _read_exact(self, length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            chunk = self.rfile.read(length - len(chunks))
            if not chunk:
                raise EOFError
            chunks.extend(chunk)
        return bytes(chunks)

    def _send_websocket_frame(self, opcode: int, payload: bytes = b"") -> None:
        first = bytes((0x80 | opcode,))
        length = len(payload)
        if length < 126:
            header = first + bytes((length,))
        elif length <= 0xFFFF:
            header = first + bytes((126,)) + length.to_bytes(2, "big")
        else:
            header = first + bytes((127,)) + length.to_bytes(8, "big")
        self.wfile.write(header + payload)
        self.wfile.flush()

    def _send_websocket_close(self, code: int) -> None:
        with suppress(OSError):
            self._send_websocket_frame(0x8, code.to_bytes(2, "big"))

    def _require_admin(self) -> None:
        if not is_loopback(self.client_address[0]):
            raise ApiError(HTTPStatus.FORBIDDEN, "management API is local-only")
        supplied = self.headers.get("X-Phone-Remote-Admin", "")
        if not hmac.compare_digest(supplied, self.server.context.admin_token):
            raise ApiError(HTTPStatus.UNAUTHORIZED, "management authorization required")

    def _read_json(self) -> dict[str, Any]:
        transfer_encoding = self.headers.get("Transfer-Encoding")
        if transfer_encoding:
            raise ApiError(HTTPStatus.BAD_REQUEST, "chunked requests are not supported")
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid content length") from exc
        if length < 0:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid content length")
        if length > MAX_REQUEST_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request is too large")
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "malformed JSON") from exc
        if not isinstance(data, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "request body must be an object")
        return data

    def _serve_static(self, path: str, *, head: bool) -> bool:
        context = self.server.context
        if path in {"/", "/index.html"}:
            return self._file(context.paths.web_root / "index.html", "no-store", head=head)
        if path == "/manage" or path == "/manage/":
            if not self.server.allow_management:
                raise ApiError(HTTPStatus.FORBIDDEN, "management UI is unavailable here")
            if not is_loopback(self.client_address[0]):
                raise ApiError(HTTPStatus.FORBIDDEN, "management UI is local-only")
            return self._file(context.paths.web_root / "manage.html", "no-store", head=head)
        if path.startswith("/assets/"):
            name = unquote(path[len("/assets/") :])
            if Path(name).name != name:
                raise ApiError(HTTPStatus.NOT_FOUND, "not found")
            return self._file(
                context.paths.web_root / "assets" / name, "public, max-age=86400", head=head
            )
        if path.startswith("/app-icons/"):
            name = unquote(path[len("/app-icons/") :])
            if Path(name).name != name:
                raise ApiError(HTTPStatus.NOT_FOUND, "not found")
            return self._file(context.paths.icon_root / name, "public, max-age=86400", head=head)
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return True
        return False

    def _file(self, path: Path, cache_control: str, *, head: bool) -> bool:
        content_type = STATIC_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path)[0]
        if not path.is_file() or content_type is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "not found")
        payload = path.read_bytes()
        self._payload(HTTPStatus.OK, payload, content_type, cache_control, head=head)
        return True

    def _json(self, status: int, data: dict[str, Any], *, head: bool = False) -> None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._payload(
            status,
            payload,
            "application/json; charset=utf-8",
            "no-store",
            head=head,
        )

    def _payload(
        self,
        status: int,
        payload: bytes,
        content_type: str,
        cache_control: str,
        *,
        head: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if content_type.startswith("text/html"):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self'; "
                "script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
            )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if not head:
            self.wfile.write(payload)


def _validate_body_keys(
    data: dict[str, Any],
    *,
    required: set[str],
    allowed: set[str],
) -> None:
    missing = required - data.keys()
    if missing:
        raise ValueError(f"missing field: {sorted(missing)[0]}")
    unexpected = data.keys() - allowed
    if unexpected:
        raise ValueError(f"unexpected field: {sorted(unexpected)[0]}")


def _validate_mouse_body(data: dict[str, Any]) -> dict[str, Any]:
    kind = data.get("type")
    schemas = {
        "move": ({"type", "dx", "dy"}, {"type", "dx", "dy"}),
        "click": ({"type"}, {"type", "button"}),
        "double": ({"type"}, {"type"}),
        "wheel": ({"type", "delta"}, {"type", "delta"}),
    }
    if not isinstance(kind, str) or kind not in schemas:
        raise ValueError("unknown mouse event")
    required, allowed = schemas[kind]
    _validate_body_keys(data, required=required, allowed=allowed)
    return data


def _body_text(data: dict[str, Any], key: str, maximum: int) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"invalid {key}")
    return value.strip()
