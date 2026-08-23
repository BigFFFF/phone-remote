# Protocol

`protocol/openapi.yaml` is the authoritative API v1 contract.

## Endpoints

| Client | Transport | Default port |
| --- | --- | --- |
| Native mobile app | HTTPS with pinned Server Identity | 8765 |
| Browser Web Remote | Plain HTTP on trusted Private LAN only | 8766 |

Companion advertises `_phone-remote._tcp.local.`; manual host/IP entry is the fallback.

## Pairing and authentication

The client requests a session, enters the one-time six-digit code shown by Companion, and receives
its client ID and credential once. Pairing expires after five minutes and is rate/attempt limited.
Authenticated routes use `Authorization: Bearer <credential>`, and each client can be revoked
independently. Native clients pin the Server ID and identity fingerprint.

Wake on LAN is an explicit mobile action. Ordinary startup, reconnect, and saved-device selection
never send a magic packet automatically.

## Control boundary

Remote requests accept only enumerated actions, bounded mouse values, up to 2,000 Unicode
characters, power actions, or approved application IDs. Paths, URLs, shell commands, and arbitrary
command lines are rejected. Request bodies are limited to 16 KiB.

`sleep` and `hibernate` request Windows standby and hibernation; actual behavior and Wake on LAN
support depend on firmware, Windows policy, and the network adapter.

Product versions may differ while both sides report `apiVersion: 1`. New clients use `/api/v1/*`;
legacy authenticated aliases remain for compatibility.
