from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import ssl
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from .state import StateStore


class IdentityChangedError(RuntimeError):
    pass


@dataclass(frozen=True)
class ServerIdentity:
    server_id: str
    install_id: str
    display_name: str
    fingerprint: str
    certificate_fingerprint: str


class IdentityManager:
    def __init__(
        self,
        state: StateStore,
        identity_key_path: Path,
        certificate_path: Path,
        tls_key_path: Path,
    ):
        self.state = state
        self.identity_key_path = identity_key_path
        self.certificate_path = certificate_path
        self.tls_key_path = tls_key_path

    def ensure(self, display_name: str | None = None) -> ServerIdentity:
        key = self._load_or_create_key()
        fingerprint = _public_key_fingerprint(key)
        state = self.state.read()
        server = state["server"]
        recorded = server.get("identity_fingerprint")
        if recorded and recorded != fingerprint:
            raise IdentityChangedError(
                "server identity key changed unexpectedly; restore the original key or reset state"
            )
        changed = False
        if not server.get("server_id"):
            server["server_id"] = str(uuid.uuid4())
            changed = True
        if not server.get("install_id"):
            server["install_id"] = str(uuid.uuid4())
            changed = True
        if not server.get("display_name"):
            server["display_name"] = display_name or socket.gethostname()
            changed = True
        if not recorded:
            server["identity_fingerprint"] = fingerprint
            changed = True
        if not server.get("created_at"):
            server["created_at"] = datetime.now(UTC).isoformat()
            changed = True
        if changed:
            self.state.write(state)

        certificate = self._load_or_create_certificate(
            key, server["server_id"], server["display_name"]
        )
        return ServerIdentity(
            server_id=server["server_id"],
            install_id=server["install_id"],
            display_name=server["display_name"],
            fingerprint=fingerprint,
            certificate_fingerprint=hashlib.sha256(
                certificate.public_bytes(serialization.Encoding.DER)
            ).hexdigest(),
        )

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(self.certificate_path), str(self.tls_key_path))
        return context

    def _load_or_create_key(self) -> ec.EllipticCurvePrivateKey:
        self.identity_key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.identity_key_path.exists():
            value = serialization.load_pem_private_key(
                self.identity_key_path.read_bytes(), password=None
            )
            if not isinstance(value, ec.EllipticCurvePrivateKey) or not isinstance(
                value.curve, ec.SECP256R1
            ):
                raise ValueError("server identity key has an unexpected type")
            return value
        key = ec.generate_private_key(ec.SECP256R1())
        _private_write(
            self.identity_key_path,
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        )
        return key

    def _load_or_create_certificate(
        self, key: ec.EllipticCurvePrivateKey, server_id: str, display_name: str
    ) -> x509.Certificate:
        if self.certificate_path.exists() and self.tls_key_path.exists():
            try:
                certificate = x509.load_pem_x509_certificate(self.certificate_path.read_bytes())
                certificate_key = certificate.public_key().public_bytes(
                    serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                identity_key = key.public_key().public_bytes(
                    serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                renewal_threshold = datetime.now(UTC) + timedelta(days=30)
                if (
                    certificate_key == identity_key
                    and certificate.not_valid_after_utc > renewal_threshold
                ):
                    _private_write(
                        self.tls_key_path,
                        key.private_bytes(
                            serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption(),
                        ),
                    )
                    return certificate
            except (ValueError, OSError):
                pass

        now = datetime.now(UTC)
        subject = x509.Name(
            [
                (x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Phone Remote")),
                (x509.NameAttribute(NameOID.COMMON_NAME, display_name[:64])),
            ]
        )
        host = socket.gethostname()
        sans: list[x509.GeneralName] = [
            x509.DNSName(host),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            x509.UniformResourceIdentifier(f"urn:phone-remote:server:{server_id}"),
        ]
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=397))
            .add_extension(x509.SubjectAlternativeName(sans), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, algorithm=hashes.SHA256())
        )
        _private_write(
            self.tls_key_path,
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        )
        _private_write(self.certificate_path, certificate.public_bytes(serialization.Encoding.PEM))
        return certificate


def _public_key_fingerprint(key: ec.EllipticCurvePrivateKey) -> str:
    public = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(public).hexdigest()


def _private_write(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    with suppress(OSError):
        os.chmod(temporary, 0o600)
    os.replace(temporary, path)
