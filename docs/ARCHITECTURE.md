# Architecture

Phone Remote transports control events from an authorized LAN client to a Windows PC. It does not
provide screen capture, video streaming, or display transport.

## Components

```text
Flutter app ── HTTPS 8765 + pinned identity ──┐
Web Remote ── Private-LAN HTTP 8766 ─────────┤
                                               ▼
Windows Companion
  pairing/auth ─ control ─ approved app launch
  discovery/catalog ─ mDNS ─ tray/management UI
```

The Flutter app keeps UI, discovery, pairing, sessions, Wake on LAN, device metadata, and secure
credentials separate. Pointer movement is coalesced before transmission. Demo mode is local and
does not contact the LAN.

The Companion exposes two remote transports and a loopback-only management API. Control commands
are serialized. Application discovery produces candidates; only applications approved locally are
exposed to remote clients.

## Trust and state

Mutable state lives in `%LOCALAPPDATA%\PhoneRemote`:

```text
config.json  state.json  server-identity.key  server.crt  server.key  icons/  logs/
```

The Server Identity remains stable across certificate renewal. Client credentials are stored as
salted verifiers on Windows and in Android Keystore/iOS Keychain-backed storage on mobile.

## Sources of truth

- API contract: `protocol/openapi.yaml`
- Runtime configuration schema: `config.example.json` and server validation code
- Current release state: `docs/RELEASE_GATE.md`
