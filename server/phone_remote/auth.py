from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .state import StateStore

TOKEN_PREFIX = "pr1"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
SECRET_BYTES = 32


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _verifier(secret: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        secret.encode("ascii"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )


@dataclass(frozen=True)
class IssuedCredential:
    client_id: str
    credential: str
    device_name: str
    platform: str


class CredentialStore:
    def __init__(self, state: StateStore):
        self.state = state

    def issue(self, device_name: str, platform: str) -> IssuedCredential:
        device_name = _metadata_text(device_name, "device name", 120)
        platform = _metadata_text(platform, "platform", 40)
        client_id = str(uuid.uuid4())
        secret = _encode(secrets.token_bytes(SECRET_BYTES))
        salt = secrets.token_bytes(SALT_BYTES)
        now = utc_now()
        record = {
            "client_id": client_id,
            "device_name": device_name,
            "platform": platform,
            "credential_salt": _encode(salt),
            "credential_verifier": _encode(_verifier(secret, salt)),
            "created_at": now,
            "last_seen": now,
            "revoked_at": None,
        }

        def add(state: dict[str, Any]) -> None:
            state["clients"].append(record)

        self.state.update(add)
        credential = f"{TOKEN_PREFIX}.{client_id}.{secret}"
        return IssuedCredential(client_id, credential, device_name, platform)

    def authenticate(
        self, credential: str, *, update_last_seen: bool = True
    ) -> dict[str, Any] | None:
        parsed = self._parse(credential)
        if parsed is None:
            return None
        client_id, secret = parsed
        state = self.state.read()
        record = next(
            (item for item in state["clients"] if item.get("client_id") == client_id), None
        )
        if not isinstance(record, dict) or record.get("revoked_at"):
            return None
        try:
            expected = _decode(record["credential_verifier"])
            actual = _verifier(secret, _decode(record["credential_salt"]))
        except (KeyError, TypeError, ValueError):
            return None
        if not hmac.compare_digest(actual, expected):
            return None
        if update_last_seen and _last_seen_is_stale(record):
            now = utc_now()

            def touch(value: dict[str, Any]) -> None:
                for item in value["clients"]:
                    if item.get("client_id") == client_id and not item.get("revoked_at"):
                        item["last_seen"] = now
                        break

            self.state.update(touch)
            record["last_seen"] = now
        return _public_record(record)

    def list_clients(self, *, include_revoked: bool = False) -> list[dict[str, Any]]:
        records = self.state.read()["clients"]
        return [
            _public_record(item)
            for item in records
            if isinstance(item, dict) and (include_revoked or not item.get("revoked_at"))
        ]

    def revoke(self, client_id: str) -> bool:
        revoked = False

        def mutate(state: dict[str, Any]) -> None:
            nonlocal revoked
            for item in state["clients"]:
                if item.get("client_id") == client_id and not item.get("revoked_at"):
                    item["revoked_at"] = utc_now()
                    revoked = True
                    return

        self.state.update(mutate)
        return revoked

    def revoke_all(self) -> int:
        count = 0

        def mutate(state: dict[str, Any]) -> None:
            nonlocal count
            now = utc_now()
            for item in state["clients"]:
                if not item.get("revoked_at"):
                    item["revoked_at"] = now
                    count += 1

        self.state.update(mutate)
        return count

    @staticmethod
    def _parse(credential: str) -> tuple[str, str] | None:
        if not isinstance(credential, str) or len(credential) > 256:
            return None
        parts = credential.split(".")
        if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
            return None
        try:
            uuid.UUID(parts[1])
            secret = _decode(parts[2])
        except (ValueError, TypeError):
            return None
        if len(secret) != SECRET_BYTES:
            return None
        return parts[1], parts[2]


def _metadata_text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"invalid {field}")
    return value.strip()


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "client_id",
            "device_name",
            "platform",
            "created_at",
            "last_seen",
            "revoked_at",
        )
    }


def _last_seen_is_stale(record: dict[str, Any]) -> bool:
    try:
        last_seen = datetime.fromisoformat(str(record["last_seen"]))
    except (KeyError, TypeError, ValueError):
        return True
    return (datetime.now(UTC) - last_seen).total_seconds() >= 60
