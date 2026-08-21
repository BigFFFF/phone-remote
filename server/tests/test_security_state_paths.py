import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
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


def test_server_identity_and_certificate_persist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("phone_remote.security.local_ipv4_addresses", lambda: ["192.168.1.20"])
    manager = identity_manager(tmp_path)
    first = manager.ensure("Living Room PC")
    second = identity_manager(tmp_path).ensure("Ignored New Name")
    assert first == second
    assert len(first.fingerprint) == 64
    assert len(first.certificate_fingerprint) == 64
    assert (tmp_path / "server.crt").read_text().startswith("-----BEGIN CERTIFICATE-----")
    assert (tmp_path / "server.crt").read_text().count("-----BEGIN CERTIFICATE-----") == 1

    certificate = x509.load_pem_x509_certificate((tmp_path / "server.crt").read_bytes())
    certificate.verify_directly_issued_by(certificate)
    assert not certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    sans = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "192.168.1.20" in {str(value) for value in sans.get_values_for_type(x509.IPAddress)}
    assert manager.create_ssl_context()


def test_certificate_is_reissued_for_a_new_lan_address_without_changing_identity(
    tmp_path: Path, monkeypatch
) -> None:
    addresses = ["192.168.1.20"]
    monkeypatch.setattr("phone_remote.security.local_ipv4_addresses", lambda: addresses)
    manager = identity_manager(tmp_path)
    first = manager.ensure("PC")

    addresses[:] = ["192.168.1.21"]
    second = identity_manager(tmp_path).ensure("PC")
    certificate = x509.load_pem_x509_certificate((tmp_path / "server.crt").read_bytes())
    sans = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    ip_addresses = {str(value) for value in sans.get_values_for_type(x509.IPAddress)}

    assert first.fingerprint == second.fingerprint
    assert first.server_id == second.server_id
    assert first.certificate_fingerprint != second.certificate_fingerprint
    assert "192.168.1.21" in ip_addresses


def test_legacy_certificate_without_lan_san_is_reissued(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("phone_remote.security.local_ipv4_addresses", lambda: ["192.168.1.20"])
    manager = identity_manager(tmp_path)
    original_identity = manager.ensure("PC")
    identity_key = serialization.load_pem_private_key(
        (tmp_path / "identity.key").read_bytes(), password=None
    )
    assert isinstance(identity_key, ec.EllipticCurvePrivateKey)
    subject = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "PC")])
    now = datetime.now(UTC)
    legacy_certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(identity_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=397))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(identity_key, hashes.SHA256())
    )
    (tmp_path / "server.crt").write_bytes(
        legacy_certificate.public_bytes(serialization.Encoding.PEM)
    )

    migrated_identity = identity_manager(tmp_path).ensure("PC")
    migrated_certificate = x509.load_pem_x509_certificate((tmp_path / "server.crt").read_bytes())
    migrated_certificate.verify_directly_issued_by(migrated_certificate)
    sans = migrated_certificate.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value
    assert migrated_identity.fingerprint == original_identity.fingerprint
    assert migrated_identity.server_id == original_identity.server_id
    assert migrated_identity.certificate_fingerprint != original_identity.certificate_fingerprint
    assert "192.168.1.20" in {str(value) for value in sans.get_values_for_type(x509.IPAddress)}


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


def test_runtime_paths_use_current_bundle_without_legacy_import(tmp_path: Path) -> None:
    executable = tmp_path / "installed"
    bundle = tmp_path / "bundle"
    data = tmp_path / "data"
    executable.mkdir()
    (executable / "icons").mkdir()
    bundle.mkdir()
    (bundle / "web").mkdir()
    (bundle / "resources" / "icons").mkdir(parents=True)
    (bundle / "config.example.json").write_text('{"current":true}', encoding="utf-8")
    (bundle / "resources" / "icons" / "default.svg").write_text("current", encoding="utf-8")
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
    assert paths.config_path.read_text() == '{"current":true}'
    assert (paths.icon_root / "default.svg").read_text() == "current"
    assert not (paths.icon_root / "app.png").exists()
    paths.config_path.write_text("user-change", encoding="utf-8")
    paths.prepare()
    assert paths.config_path.read_text() == "user-change"
