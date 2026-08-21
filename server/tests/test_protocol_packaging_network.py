import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from phone_remote.api import ApiContext
from phone_remote.discovery import DiscoveryPublisher
from phone_remote.network import (
    API_FIREWALL_RULE,
    DISCOVERY_FIREWALL_RULE,
    NetworkDiagnostics,
    firewall_install_commands,
    firewall_remove_command,
    local_ipv4_addresses,
    set_start_with_windows,
)
from phone_remote.security import ServerIdentity
from phone_remote.server import ServerRuntime, build_parser, main

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_firewall_commands_are_private_program_specific_and_local_subnet(tmp_path: Path) -> None:
    executable = tmp_path / "Phone Remote" / "PhoneRemote.exe"
    commands = firewall_install_commands(executable, 8765, 8766)
    assert commands[0] == firewall_remove_command(API_FIREWALL_RULE)
    assert commands[1] == firewall_remove_command(DISCOVERY_FIREWALL_RULE)
    api = commands[2]
    discovery = commands[3]
    for command in (api, discovery):
        joined = " ".join(command).lower()
        assert "profile=private" in joined
        assert "remoteip=localsubnet" in joined
        assert "phoneremote.exe" in joined
        assert "profile=public" not in joined
        assert "dir=out" not in joined
    assert "protocol=tcp" in " ".join(api).lower()
    assert "localport=8765,8766" in " ".join(api).lower()
    assert "protocol=udp" in " ".join(discovery).lower()
    assert "localport=5353" in " ".join(discovery).lower()


def test_public_network_policy_blocks_non_loopback_only(monkeypatch) -> None:
    context = object.__new__(ApiContext)
    context._profile_lock = __import__("threading").Lock()
    context._profile_checked_at = 0.0
    context._public_only = False

    class Network:
        def public_only(self):
            return True

    context.network = Network()
    assert context.remote_allowed("127.0.0.1") is True
    assert context.remote_allowed("192.168.1.20") is False


def test_private_lan_classification_rejects_public_addresses() -> None:
    from phone_remote.network import is_private_lan

    assert is_private_lan("127.0.0.1") is True
    assert is_private_lan("192.168.1.20") is True
    assert is_private_lan("10.0.0.8") is True
    assert is_private_lan("169.254.10.20") is True
    assert is_private_lan("8.8.8.8") is False
    assert is_private_lan("invalid") is False


def test_local_addresses_prefer_active_physical_lan_over_proxy_ip(monkeypatch) -> None:
    import phone_remote.network as network

    monkeypatch.setattr(network.sys, "platform", "win32")
    monkeypatch.setattr(
        network,
        "_windows_physical_ipv4_addresses",
        lambda: ("28.0.0.1", "169.254.10.20", "192.168.31.124"),
    )

    assert local_ipv4_addresses() == ["169.254.10.20", "192.168.31.124"]


def test_physical_address_cache_refreshes_after_its_ttl(monkeypatch) -> None:
    import phone_remote.network as network

    now = [100.0]
    responses = iter([("192.168.1.20",), ("192.168.1.21",)])
    calls = []
    monkeypatch.setattr(network.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        network,
        "_query_windows_physical_ipv4_addresses",
        lambda: calls.append(now[0]) or next(responses),
    )
    monkeypatch.setattr(network, "_physical_address_cache", ())
    monkeypatch.setattr(network, "_physical_address_cached_at", float("-inf"))

    assert network._windows_physical_ipv4_addresses() == ("192.168.1.20",)
    now[0] += network.PHYSICAL_ADDRESS_CACHE_SECONDS - 1
    assert network._windows_physical_ipv4_addresses() == ("192.168.1.20",)
    now[0] += 2
    assert network._windows_physical_ipv4_addresses() == ("192.168.1.21",)
    assert calls == [100.0, 116.0]


def test_browser_listener_has_a_separate_default_port() -> None:
    args = build_parser().parse_args([])
    assert args.port == 8765
    assert args.web_port == 8766
    with pytest.raises(SystemExit, match="web port must differ"):
        main(["--port", "9000", "--web-port", "9000"])


def test_runtime_stops_background_listeners_before_closing_sockets() -> None:
    runtime = object.__new__(ServerRuntime)
    runtime.http = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    runtime.web_http = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    runtime.publisher = SimpleNamespace(close=lambda: None)
    runtime.logger = logging.getLogger("phone_remote.test.lifecycle")
    runtime._server_threads = []
    runtime._start_background_server(runtime.http, "test-api")
    runtime._start_background_server(runtime.web_http, "test-web")

    runtime.close()

    assert all(not thread.is_alive() for thread in runtime._server_threads)
    assert runtime.http.fileno() == -1
    assert runtime.web_http.fileno() == -1


def test_startup_registration_preserves_executable_and_arguments(monkeypatch) -> None:
    import phone_remote.network as network

    recorded = {}

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(network.winreg, "CreateKeyEx", lambda *_args, **_kwargs: Key())
    monkeypatch.setattr(
        network.winreg,
        "SetValueEx",
        lambda _key, name, _reserved, _kind, value: recorded.update(name=name, value=value),
    )
    set_start_with_windows([r"C:\Program Files\Python 3.12\python.exe", "-m", "phone_remote"], True)
    assert recorded["name"] == "Phone Remote"
    assert recorded["value"] == '"C:\\Program Files\\Python 3.12\\python.exe" -m phone_remote'


def test_wake_targets_normalize_mac_and_compute_directed_broadcast(monkeypatch) -> None:
    import phone_remote.network as network

    calls = []
    monkeypatch.setattr(network.sys, "platform", "win32")
    monkeypatch.setattr(
        network.subprocess,
        "run",
        lambda *args, **kwargs: (
            calls.append((args, kwargs))
            or SimpleNamespace(
                returncode=0,
                stdout=(
                    '[{"mac":"00-11-22-33-44-55","address":"192.168.10.20","prefixLength":24}]'
                ),
            )
        ),
    )
    diagnostics = NetworkDiagnostics()

    assert diagnostics.wake_targets() == [
        {
            "mac": "00:11:22:33:44:55",
            "address": "192.168.10.20",
            "broadcast": "192.168.10.255",
        }
    ]
    assert diagnostics.wake_targets() == diagnostics.wake_targets()
    assert len(calls) == 1
    assert calls[0][1]["creationflags"] != 0


def test_web_pairing_ignores_only_responses_from_replaced_credentials() -> None:
    page = (REPOSITORY_ROOT / "server" / "web" / "index.html").read_text(encoding="utf-8")
    assert "const requestCredential = credential;" in page
    assert "if (requestCredential !== credential) return response;" in page
    success = page.index("localStorage.setItem('phone-remote-identity', identityFingerprint);")
    reset = page.index("pairingSessionId = '';", success)
    refresh = page.index("refresh(); refreshApps();", success)
    assert success < reset < refresh
    assert page.count("if (!credential) return;") >= 2


def test_discovery_failure_never_blocks_manual_connection(monkeypatch) -> None:
    import phone_remote.discovery as discovery

    identity = ServerIdentity("server", "install", "PC", "a" * 64, "b" * 64)
    publisher = DiscoveryPublisher(identity, 8765, logging.getLogger("discovery-test"))
    monkeypatch.setattr(discovery, "local_ipv4_addresses", lambda: ["192.168.1.2"])
    monkeypatch.setattr(discovery, "Zeroconf", lambda **_kwargs: (_ for _ in ()).throw(OSError()))
    assert publisher.start() is False
    assert publisher.zeroconf is None


def test_discovery_without_lan_address_is_a_nonfatal_noop(monkeypatch) -> None:
    import phone_remote.discovery as discovery

    identity = ServerIdentity("server", "install", "PC", "a" * 64, "b" * 64)
    publisher = DiscoveryPublisher(identity, 8765, logging.getLogger("discovery-test"))
    monkeypatch.setattr(discovery, "local_ipv4_addresses", lambda: [])
    assert publisher.start() is False


def test_openapi_contract_has_security_and_all_control_routes() -> None:
    document = yaml.safe_load((REPOSITORY_ROOT / "protocol" / "openapi.yaml").read_text())
    assert document["openapi"].startswith("3.1")
    assert document["components"]["securitySchemes"]["bearerCredential"]["scheme"] == "bearer"
    expected = {
        "/info",
        "/pair/request",
        "/pair/complete",
        "/status",
        "/apps",
        "/apps/{appId}/launch",
        "/action",
        "/mouse",
        "/text",
        "/power",
    }
    assert set(document["paths"]) == expected
    assert document["paths"]["/info"]["get"]["security"] == []
    assert document["paths"]["/pair/request"]["post"]["security"] == []
    assert "security" not in document["paths"]["/status"]["get"]


def test_installer_owns_only_minimal_firewall_rules_and_preserves_data() -> None:
    installer = (REPOSITORY_ROOT / "packaging" / "windows" / "installer.iss").read_text()
    lowered = installer.lower()
    assert "profile=private" in lowered
    assert "remoteip=localsubnet" in lowered
    assert "localport=8765,8766" in lowered
    assert "profile=public" not in lowered
    assert "firewall set opmode disable" not in lowered
    assert "dir=out" not in lowered
    assert "removeuserdata" in lowered
    assert "{localappdata}\\phoneremote" in lowered
    assert "uninstallrun" in lowered


def test_ci_pins_python_and_never_executes_real_power_or_firewall_mutation() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "server-ci.yml").read_text()
    assert 'python-version: "3.12"' in workflow
    assert "pytest" in workflow
    assert "PyInstaller" in workflow
    assert "netsh" not in workflow
    assert "shutdown.exe" not in workflow
