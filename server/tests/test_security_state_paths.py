import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from phone_remote.paths import RuntimePaths
from phone_remote.security import IdentityChangedError, IdentityManager
from phone_remote.state import StateStore


def identity_manager(tmp_path: Path) -> IdentityManager:
    return IdentityManager(
        StateStore(tmp_path / "state.json"),
        tmp_path / "identity.key",
        tmp_path / "server.crt",
        tmp_path / "server.key",
    )


def test_server_identity_and_certificate_persist(tmp_path: Path) -> None:
    manager = identity_manager(tmp_path)
    first = manager.ensure("Living Room PC")
    second = identity_manager(tmp_path).ensure("Ignored New Name")
    assert first == second
    assert len(first.fingerprint) == 64
    assert len(first.certificate_fingerprint) == 64
    assert (tmp_path / "server.crt").read_text().startswith("-----BEGIN CERTIFICATE-----")
    assert manager.create_ssl_context()


def test_unexpected_identity_key_change_is_rejected(tmp_path: Path) -> None:
    manager = identity_manager(tmp_path)
    manager.ensure("PC")
    replacement = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    (tmp_path / "identity.key").write_bytes(replacement)
    with pytest.raises(IdentityChangedError, match="changed unexpectedly"):
        identity_manager(tmp_path).ensure("PC")


def test_state_update_is_persistent_and_returns_result(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "nested" / "state.json")
    result = store.update(lambda state: state["server"].setdefault("name", "PC"))
    assert result == "PC"
    assert store.read()["server"]["name"] == "PC"
    assert not (tmp_path / "nested" / "state.json.tmp").exists()


def test_invalid_state_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        StateStore(path).read()


def test_runtime_paths_migrate_without_overwriting(tmp_path: Path) -> None:
    executable = tmp_path / "installed"
    bundle = tmp_path / "bundle"
    data = tmp_path / "data"
    executable.mkdir()
    (executable / "icons").mkdir()
    bundle.mkdir()
    (bundle / "web").mkdir()
    (executable / "config.json").write_text('{"legacy":true}', encoding="utf-8")
    (executable / "icons" / "app.png").write_bytes(b"legacy")
    paths = RuntimePaths(
        bundle,
        executable,
        data,
        data / "config.json",
        data / "icons",
        data / "state.json",
        data / "identity.key",
        data / "server.crt",
        data / "server.key",
        data / "logs",
        bundle / "web",
    )
    paths.prepare()
    assert paths.config_path.read_text() == '{"legacy":true}'
    assert (paths.icon_root / "app.png").read_bytes() == b"legacy"
    paths.config_path.write_text("user-change", encoding="utf-8")
    paths.prepare()
    assert paths.config_path.read_text() == "user-change"
