from __future__ import annotations

import hmac
import json
import logging
import mimetypes
import secrets
import threading
import time
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
from .network import (
    NetworkDiagnostics,
    is_loopback,
    is_private_lan,
)
from .pairing import PairingError, PairingManager, PairingRateLimited
from .paths import RuntimePaths
from .security import ServerIdentity
from .windows_control import ControlService

MAX_REQUEST_BYTES = 16 * 1024
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


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


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
    admin_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    _profile_lock: threading.Lock = field(default_factory=threading.Lock)
    _profile_checked_at: float = 0.0
    _public_only: bool = False

    def remote_allowed(self, address: str) -> bool:
        if is_loopback(address):
            return True
        now = time.monotonic()
        with self._profile_lock:
            if now - self._profile_checked_at > 15:
                self._public_only = self.network.public_only()
                self._profile_checked_at = now
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
    ):
        super().__init__(address, PhoneRemoteHandler)
        self.context = context
        self.allow_management = allow_management
        self.private_lan_only = private_lan_only


class PhoneRemoteHandler(BaseHTTPRequestHandler):
    server: PhoneRemoteServer
    server_version = "PhoneRemote/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

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
            self._read_json()
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

        legacy_paths = {
            "/api/status": "/api/v1/status",
            "/api/apps": "/api/v1/apps",
            "/api/action": "/api/v1/action",
            "/api/mouse": "/api/v1/mouse",
            "/api/text": "/api/v1/text",
        }
        path = legacy_paths.get(path, path)
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
            try:
                apps = context.config.public_apps()
                warning = context.config.error
            except ValueError as exc:
                apps, warning = [], str(exc)
            return {"ok": True, "apps": apps, "warning": warning}, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/action":
            data = self._read_json()
            action = data.get("action")
            result = context.control.action(action)
            context.logger.info("control action client=%s action=%s", client_id, action)
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/mouse":
            result = context.control.mouse(self._read_json())
            log = context.logger.debug if result["message"] == "move" else context.logger.info
            log("control action client=%s action=mouse:%s", client_id, result["message"])
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/text":
            data = self._read_json()
            result = context.control.text(data.get("text"))
            context.logger.info("control action client=%s action=text", client_id)
            return result, HTTPStatus.OK
        if method == "POST" and path == "/api/v1/power":
            data = self._read_json()
            action = data.get("action")
            result = context.control.power(action)
            context.logger.info("control action client=%s action=power:%s", client_id, action)
            return result, HTTPStatus.OK
        if method == "POST" and path.startswith("/api/v1/apps/") and path.endswith("/launch"):
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
        if method == "POST" and path == "/api/v1/admin/clients/revoke-all":
            return {"ok": True, "revoked": context.credentials.revoke_all()}
        if method == "DELETE" and path.startswith("/api/v1/admin/clients/"):
            client_id = unquote(path.rsplit("/", 1)[1])
            if not context.credentials.revoke(client_id):
                raise ApiError(HTTPStatus.NOT_FOUND, "client not found")
            return {"ok": True}
        if method == "POST" and path == "/api/v1/admin/apps/rescan":
            return {"ok": True, "candidates": context.catalog.rescan()}
        if method == "POST" and path == "/api/v1/admin/apps/approve":
            data = self._read_json()
            return {"ok": True, "app": context.catalog.approve(_body_text(data, "discoveryId", 80))}
        if method == "POST" and path == "/api/v1/admin/apps/manual-program":
            data = self._read_json()
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
        if not value.startswith(prefix):
            raise ApiError(HTTPStatus.UNAUTHORIZED, "authentication required")
        client = self.server.context.credentials.authenticate(value[len(prefix) :])
        if client is None:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "invalid or revoked credential")
        return client

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
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
            )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if not head:
            self.wfile.write(payload)


def _body_text(data: dict[str, Any], key: str, maximum: int) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"invalid {key}")
    return value.strip()
