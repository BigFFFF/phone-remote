# Architecture

Phone Remote sends control events from an authorized LAN client to a Windows PC. It does not
capture or stream the screen.

## Components

```text
Flutter app ── HTTPS 8765 + pinned identity ──┐
Web Remote ── Private-LAN HTTP 8766 ─────────┤
                                               ▼
Windows Companion
  pairing/auth ─ control ─ approved apps
  discovery ─ mDNS ─ tray/management UI
```

The native app uses pinned HTTPS; Web Remote uses HTTP only on trusted private networks. The
Companion also exposes a token-protected, loopback-only management API. Pointer events are batched
and sensitivity-adjusted, control commands are serialized, and remote clients can see only locally
approved applications. Demo mode never contacts the LAN.

## Trust and state

Mutable state lives in `%LOCALAPPDATA%\PhoneRemote`:

```text
config.json  state.json  server-identity.key  server.crt  server.key  icons/  logs/
```

Server Identity remains stable across certificate renewal. Windows stores salted credential
verifiers; mobile uses Android Keystore/iOS Keychain-backed storage. Runtime configuration lives
only in `config.json`; defaults are embedded in the Companion.

## Sources of truth

- API contract: `protocol/openapi.yaml`
- Runtime configuration schema and defaults: `server/phone_remote/config.py`
- Current release state: `docs/RELEASE_GATE.md`
