import http.client
import json
import logging
import threading
from pathlib import Path

import pytest

from phone_remote.api import ApiContext, PhoneRemoteServer
from phone_remote.app_discovery import ApplicationDiscovery
from phone_remote.app_launcher import AppLauncher
from phone_remote.auth import CredentialStore
from phone_remote.catalog import ApplicationCatalog
from phone_remote.config import ConfigStore
from phone_remote.pairing import PairingManager
from phone_remote.paths import RuntimePaths
from phone_remote.security import ServerIdentity
from phone_remote.state import StateStore
from phone_remote.windows_control import ControlService


class FakeBackend:
    def __init__(self):
        self.events = []

    def key(self, code):
        self.events.append(("key", code))

    def key_combo(self, *codes):
        self.events.append(("combo", *codes))

    def text(self, value):
        self.events.append(("text", value))

    def mouse_move(self, dx, dy):
        self.events.append(("move", dx, dy))

    def mouse_click(self, button):
        self.events.append(("click", button))

    def mouse_wheel(self, delta):
        self.events.append(("wheel", delta))

    def power(self, action):
        self.events.append(("power", action))


class FakeNetwork:
    def __init__(self, public_only=False):
        self.is_public_only = public_only

    def profiles(self):
        return []

    def public_only(self):
        return self.is_public_only

    def firewall_status(self):
        return {"api": True, "discovery": True}

    def wake_targets(self):
        return [
            {
                "mac": "00:11:22:33:44:55",
                "address": "192.168.1.20",
                "broadcast": "192.168.1.255",
            }
        ]


class RunningApi:
    def __init__(self, server, thread, context, backend):
        self.server = server
        self.thread = thread
        self.context = context
        self.backend = backend
        self.port = server.server_port

    def request(self, method, path, body=None, *, credential=None, admin=None, raw=False):
        headers = {}
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        if admin:
            headers["X-Phone-Remote-Admin"] = admin
        if raw:
            payload = body
        elif body is None:
            payload = None
        else:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, json.loads(data) if data else None, response.headers

    def pair(self, name="Web"):
        status, requested, _ = self.request("POST", "/api/v1/pair/request", {})
        assert status == 201
        status, completed, _ = self.request(
            "POST",
            "/api/v1/pair/complete",
            {
                "sessionId": requested["sessionId"],
                "code": "123456",
                "deviceName": name,
                "platform": "web",
            },
        )
        assert status == 201
        return completed


@pytest.fixture()
def api(tmp_path: Path):
    executable = tmp_path / "player.exe"
    browser = tmp_path / "browser.exe"
    executable.touch()
    browser.touch()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "browsers": {"edge": {"path": str(browser), "args": [], "fullscreenArgs": []}},
                "apps": [
                    {
                        "id": "player",
                        "name": "Player",
                        "enabled": True,
                        "icon": "player.png",
                        "launch": {"type": "program", "path": str(executable), "args": []},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    web_root = Path(__file__).resolve().parents[1] / "web"
    paths = RuntimePaths(
        web_root.parent,
        tmp_path,
        tmp_path,
        config_path,
        tmp_path / "icons",
        tmp_path / "state.json",
        tmp_path / "identity.key",
        tmp_path / "server.crt",
        tmp_path / "server.key",
        tmp_path / "logs",
        web_root,
    )
    paths.icon_root.mkdir()
    (paths.icon_root / "player.png").write_bytes(b"image")
    config = ConfigStore(config_path, paths.icon_root)
    credentials = CredentialStore(StateStore(paths.state_path))
    pairing = PairingManager(credentials, code_factory=lambda: "123456")
    backend = FakeBackend()
    launcher = AppLauncher(config, lambda *args, **kwargs: None)
    control = ControlService(backend, launcher)
    default_icon = Path(__file__).resolve().parents[1] / "resources" / "icons" / "default.svg"
    catalog = ApplicationCatalog(config, ApplicationDiscovery([]), default_icon)
    logger = logging.getLogger(f"phone_remote.test.{tmp_path.name}")
    context = ApiContext(
        identity=ServerIdentity("server-id", "install-id", "Test PC", "a" * 64, "b" * 64),
        paths=paths,
        config=config,
        credentials=credentials,
        pairing=pairing,
        control=control,
        catalog=catalog,
        network=FakeNetwork(),
        logger=logger,
        port=0,
        admin_token="admin-secret",
    )
    server = PhoneRemoteServer(("127.0.0.1", 0), context)
    context.port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    running = RunningApi(server, thread, context, backend)
    yield running
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_public_info_and_static_security_headers(api: RunningApi) -> None:
    status, info, _ = api.request("GET", "/api/v1/info")
    assert status == 200
    assert info["serverId"] == "server-id"
    assert info["apiVersion"] == 1
    connection = http.client.HTTPConnection("127.0.0.1", api.port)
    connection.request("GET", "/")
    response = connection.getresponse()
    response.read()
    assert response.status == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    connection.close()


def test_control_requires_pairing_and_accepts_valid_credential(api: RunningApi) -> None:
    assert api.request("GET", "/api/v1/status")[0] == 401
    paired = api.pair()
    credential = paired["credential"]
    status, server_status, _ = api.request("GET", "/api/v1/status", credential=credential)
    assert status == 200
    assert server_status["wakeTargets"][0]["mac"] == "00:11:22:33:44:55"
    status, _, _ = api.request("POST", "/api/v1/action", {"action": "up"}, credential=credential)
    assert status == 200
    assert api.backend.events[-1][0] == "key"


def test_revoked_credential_is_rejected_without_affecting_other_client(api: RunningApi) -> None:
    first = api.pair("First")
    second = api.pair("Second")
    status, _, _ = api.request(
        "DELETE",
        f"/api/v1/admin/clients/{first['clientId']}",
        admin="admin-secret",
    )
    assert status == 200
    assert api.request("GET", "/api/v1/status", credential=first["credential"])[0] == 401
    assert api.request("GET", "/api/v1/status", credential=second["credential"])[0] == 200


def test_validation_errors_and_request_limits(api: RunningApi) -> None:
    credential = api.pair()["credential"]
    assert (
        api.request("POST", "/api/v1/action", {"action": "cmd /c shutdown"}, credential=credential)[
            0
        ]
        == 400
    )
    assert (
        api.request("POST", "/api/v1/text", {"text": "x" * 2001}, credential=credential)[0] == 400
    )
    assert (
        api.request("POST", "/api/v1/mouse", {"type": "move", "dx": "NaN"}, credential=credential)[
            0
        ]
        == 400
    )
    status, body, _ = api.request(
        "POST", "/api/v1/action", b"{broken", credential=credential, raw=True
    )
    assert status == 400 and body["error"] == "malformed JSON"
    status, body, _ = api.request(
        "POST", "/api/v1/action", b"x" * (16 * 1024 + 1), credential=credential, raw=True
    )
    assert status == 413 and body["error"] == "request is too large"


def test_power_and_text_are_mapped_without_logging_text(api: RunningApi, caplog) -> None:
    credential = api.pair()["credential"]
    secret_text = "do-not-log-this-keyboard-text"
    with caplog.at_level(logging.INFO, logger=api.context.logger.name):
        assert (
            api.request("POST", "/api/v1/text", {"text": secret_text}, credential=credential)[0]
            == 200
        )
        assert (
            api.request("POST", "/api/v1/power", {"action": "restart"}, credential=credential)[0]
            == 200
        )
    assert ("text", secret_text) in api.backend.events
    assert ("power", "restart") in api.backend.events
    assert secret_text not in caplog.text
    assert credential not in caplog.text


def test_unknown_app_arbitrary_url_and_path_traversal_are_impossible(api: RunningApi) -> None:
    credential = api.pair()["credential"]
    assert api.request("POST", "/api/v1/apps/player/launch", {}, credential=credential)[0] == 200
    assert (
        api.request("POST", "/api/v1/action", {"action": "app:player"}, credential=credential)[0]
        == 400
    )
    assert api.request("POST", "/api/v1/apps/missing/launch", {}, credential=credential)[0] == 400
    assert (
        api.request(
            "POST",
            "/api/v1/apps/https%3A%2F%2Fevil.example/launch",
            {},
            credential=credential,
        )[0]
        == 400
    )
    assert api.request("GET", "/assets/%2e%2e%2fstate.json")[0] == 404


def test_admin_api_is_token_protected(api: RunningApi) -> None:
    assert api.request("GET", "/api/v1/admin/overview")[0] == 401
    assert api.request("GET", "/api/v1/admin/pair", admin="admin-secret")[0] == 404
    assert api.request("POST", "/api/v1/pair/request", {})[0] == 201
    status, data, _ = api.request("GET", "/api/v1/admin/pair", admin="admin-secret")
    assert status == 200 and data["code"] == "123456"
    assert api.request("GET", "/api/v1/admin/overview", admin="admin-secret")[0] == 200


def test_legacy_routes_are_authenticated_during_migration(api: RunningApi) -> None:
    assert api.request("GET", "/api/status")[0] == 401
    credential = api.pair()["credential"]
    assert api.request("GET", "/api/status", credential=credential)[0] == 200
    assert api.request("GET", "/api/apps", credential=credential)[0] == 200
