from pathlib import Path

import pytest

from phone_remote.auth import CredentialStore
from phone_remote.pairing import PairingError, PairingManager, PairingRateLimited
from phone_remote.state import StateStore


@pytest.fixture()
def credentials(tmp_path: Path) -> CredentialStore:
    return CredentialStore(StateStore(tmp_path / "state.json"))


def test_credentials_are_independent_hashed_and_persistent(
    credentials: CredentialStore, tmp_path: Path
) -> None:
    first = credentials.issue("Alice's phone", "ios")
    second = credentials.issue("Tablet", "android")
    raw = (tmp_path / "state.json").read_text(encoding="utf-8")
    assert first.credential not in raw
    assert second.credential not in raw
    assert credentials.authenticate(first.credential)["client_id"] == first.client_id
    assert credentials.authenticate(second.credential)["client_id"] == second.client_id

    reloaded = CredentialStore(StateStore(tmp_path / "state.json"))
    assert reloaded.authenticate(first.credential)["device_name"] == "Alice's phone"


def test_independent_revocation_and_revoke_all(credentials: CredentialStore) -> None:
    first = credentials.issue("First", "web")
    second = credentials.issue("Second", "web")
    assert credentials.revoke(first.client_id)
    assert credentials.authenticate(first.credential) is None
    assert credentials.authenticate(second.credential) is not None
    assert credentials.revoke_all() == 1
    assert credentials.authenticate(second.credential) is None
    assert credentials.revoke("missing") is False


@pytest.mark.parametrize(
    "credential",
    ["", "Bearer token", "pr1.not-a-uuid.secret", "pr1.00000000-0000-0000-0000-000000000000.short"],
)
def test_malformed_credentials_are_rejected(credentials: CredentialStore, credential: str) -> None:
    assert credentials.authenticate(credential) is None


def test_pairing_is_one_time_and_issues_client(credentials: CredentialStore) -> None:
    now = [100.0]
    manager = PairingManager(
        credentials,
        clock=lambda: now[0],
        code_factory=lambda: "123456",
    )
    session = manager.start("192.168.1.20")
    assert session.code is None
    issued = manager.complete(session.session_id, "123456", "Phone", "android")
    assert credentials.authenticate(issued.credential)["client_id"] == issued.client_id
    with pytest.raises(PairingError, match="invalid pairing session"):
        manager.complete(session.session_id, "123456", "Phone", "android")


def test_new_pairing_request_invalidates_old_session(credentials: CredentialStore) -> None:
    manager = PairingManager(credentials, code_factory=lambda: "123456")
    old = manager.start("client")
    new = manager.start("client")
    assert old.session_id != new.session_id
    with pytest.raises(PairingError, match="invalid pairing session"):
        manager.complete(old.session_id, "123456", "Phone", "web")


def test_pairing_expiration_attempt_limit_and_request_rate_limit(
    credentials: CredentialStore,
) -> None:
    now = [100.0]
    manager = PairingManager(
        credentials,
        lifetime_seconds=10,
        maximum_attempts=2,
        requests_per_minute=2,
        clock=lambda: now[0],
        code_factory=lambda: "654321",
    )
    expired = manager.start("expired")
    now[0] = 111.0
    with pytest.raises(PairingError, match="expired"):
        manager.complete(expired.session_id, "654321", "Phone", "web")

    now[0] = 200.0
    limited = manager.start("attempts")
    with pytest.raises(PairingError, match="incorrect"):
        manager.complete(limited.session_id, "000000", "Phone", "web")
    with pytest.raises(PairingRateLimited, match="attempt limit"):
        manager.complete(limited.session_id, "000000", "Phone", "web")

    manager.start("requests")
    manager.start("requests")
    with pytest.raises(PairingRateLimited, match="too many"):
        manager.start("requests")
    now[0] += 61
    assert manager.start("requests").session_id


def test_pairing_notifier_receives_secret_but_view_does_not(credentials: CredentialStore) -> None:
    notifications = []
    manager = PairingManager(
        credentials,
        code_factory=lambda: "123456",
        notifier=lambda code, lifetime: notifications.append((code, lifetime)),
    )
    view = manager.start("client")
    assert view.code is None
    assert notifications == [("123456", 300)]
