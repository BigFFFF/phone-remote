# Protocol

`protocol/openapi.yaml` is the authoritative API v1 contract.

## Endpoints

| Client | Transport | Default port |
| --- | --- | --- |
| Native mobile app | HTTPS with pinned Server Identity | 8765 |
| Browser Web Remote | Plain HTTP on trusted Private LAN only | 8766 |

Companion advertises `_phone-remote._tcp.local.`. Manual host/IP entry remains available.

## Pairing and authentication

1. The client requests a pairing session.
2. Companion displays a one-time six-digit code.
3. The client completes pairing with the code and receives its client ID and Credential once.
4. Authenticated routes use `Authorization: Bearer <credential>`.

Pairing sessions expire after five minutes and are rate/attempt limited. Each client has an
independently revocable Credential. Native clients retain the Server ID and identity fingerprint
and block unexpected identity changes.

Wake on LAN is an explicit mobile action. Ordinary startup, reconnect, and saved-device selection
never send a magic packet automatically.

## Control boundary

Remote requests contain only enumerated actions, bounded mouse values, text up to 2,000 Unicode
characters, a power action, or an approved application ID. Executable paths, URLs, shell commands,
and arbitrary command lines are not accepted. Request bodies are limited to 16 KiB.

The `sleep` and `hibernate` power actions request Windows standby and hibernation. The actual power
state and Wake on LAN availability remain subject to the PC firmware, Windows power policy, and
network adapter support.

Product versions may differ while both sides report `apiVersion: 1`. New clients use `/api/v1/*`;
legacy authenticated aliases remain for compatibility.
