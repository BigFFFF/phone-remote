from __future__ import annotations

import hmac
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

from .auth import CredentialStore, IssuedCredential


class PairingError(ValueError):
    pass


class PairingRateLimited(PairingError):
    pass


@dataclass(frozen=True)
class PairingSessionView:
    session_id: str
    expires_in: int
    code: str | None = None


@dataclass
class _Session:
    session_id: str
    code: str
    expires_at: float
    attempts: int = 0


class PairingManager:
    def __init__(
        self,
        credentials: CredentialStore,
        *,
        lifetime_seconds: int = 300,
        maximum_attempts: int = 5,
        requests_per_minute: int = 6,
        clock: Callable[[], float] = time.monotonic,
        code_factory: Callable[[], str] | None = None,
        notifier: Callable[[str, int], None] | None = None,
    ):
        self.credentials = credentials
        self.lifetime_seconds = lifetime_seconds
        self.maximum_attempts = maximum_attempts
        self.requests_per_minute = requests_per_minute
        self.clock = clock
        self.code_factory = code_factory or (lambda: f"{secrets.randbelow(1_000_000):06d}")
        self.notifier = notifier
        self._lock = threading.RLock()
        self._session: _Session | None = None
        self._request_times: dict[str, deque[float]] = defaultdict(deque)

    def start(self, source: str, *, reveal_code: bool = False) -> PairingSessionView:
        now = self.clock()
        with self._lock:
            recent = self._request_times[source]
            while recent and now - recent[0] >= 60:
                recent.popleft()
            if len(recent) >= self.requests_per_minute:
                raise PairingRateLimited("too many pairing requests")
            recent.append(now)
            code = self.code_factory()
            if len(code) != 6 or not code.isdigit():
                raise RuntimeError("pairing code factory returned an invalid code")
            self._session = _Session(
                session_id=str(uuid.uuid4()),
                code=code,
                expires_at=now + self.lifetime_seconds,
            )
            view = PairingSessionView(
                self._session.session_id,
                self.lifetime_seconds,
                code if reveal_code else None,
            )
        if self.notifier is not None:
            self.notifier(code, self.lifetime_seconds)
        return view

    def complete(
        self,
        session_id: str,
        code: str,
        device_name: str,
        platform: str,
    ) -> IssuedCredential:
        with self._lock:
            session = self._session
            now = self.clock()
            if session is None or session.session_id != session_id:
                raise PairingError("invalid pairing session")
            if now >= session.expires_at:
                self._session = None
                raise PairingError("pairing code expired")
            if not isinstance(code, str) or not hmac.compare_digest(session.code, code):
                session.attempts += 1
                if session.attempts >= self.maximum_attempts:
                    self._session = None
                    raise PairingRateLimited("pairing attempt limit reached")
                raise PairingError("incorrect pairing code")
            self._session = None
        return self.credentials.issue(device_name, platform)

    def active(self, *, reveal_code: bool = False) -> PairingSessionView | None:
        with self._lock:
            if self._session is None:
                return None
            remaining = int(self._session.expires_at - self.clock())
            if remaining <= 0:
                self._session = None
                return None
            return PairingSessionView(
                self._session.session_id,
                remaining,
                self._session.code if reveal_code else None,
            )

    def cancel(self) -> None:
        with self._lock:
            self._session = None
