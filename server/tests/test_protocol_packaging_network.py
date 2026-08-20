import logging
from pathlib import Path

import yaml

from phone_remote.api import ApiContext
from phone_remote.discovery import DiscoveryPublisher
from phone_remote.network import (
    API_FIREWALL_RULE,
    DISCOVERY_FIREWALL_RULE,
    firewall_install_commands,
    firewall_remove_command,
    set_start_with_windows,
)
from phone_remote.security import ServerIdentity

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_firewall_commands_are_private_program_specific_and_local_subnet(tmp_path: Path) -> None:
    executable = tmp_path / "Phone Remote" / "PhoneRemote.exe"
    commands = firewall_install_commands(executable, 8765)
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
    assert "localport=8765" in " ".join(api).lower()
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
