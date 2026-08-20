# Protocol

The authoritative machine-readable contract is `protocol/openapi.yaml`.

## Discovery and compatibility

Windows Companion advertises `_phone-remote._tcp.local.` with Server ID, display name, server
version, API version, port, TLS flag, and a short identity hint. Automatic discovery is optional;
clients must retain a manual host/IP path. `GET /api/v1/info` is public and returns the full
identity and certificate fingerprints.

A client supporting API v1 may connect to any server product version that reports
`apiVersion: 1`. An unsupported API version must produce an update message rather than a crash.

## Pairing

1. Client calls `POST /api/v1/pair/request`.
2. Companion creates one cryptographically random six-digit code and displays it on Windows.
3. Client submits the session ID, code, device name, and platform to `/pair/complete`.
4. Server returns a unique client ID and a 256-bit Credential exactly once.
5. Client stores Server ID, identity fingerprint, and Credential in secure storage.

The session lasts five minutes, is single-use, and has both wrong-attempt and request-rate
limits. Starting another session invalidates the prior session.

## Authentication and trust

Authenticated routes use `Authorization: Bearer <credential>`. Each Credential belongs to one
client. Removing one client does not affect others. There is no fixed 30/90/365-day expiration;
the relationship remains valid until explicit revocation, lost state, or identity failure.

Certificate renewal reuses the Server Identity key, so the identity fingerprint remains stable.
A client must block an unexpected fingerprint or Server ID change and require intentional
re-pairing. A client must never implement a global `trustAllCertificates` policy.

## Control contract

The client sends enumerated actions, clamped mouse values, up to 2,000 Unicode characters, a
power enum, or a configured application ID. It cannot provide an EXE path, URL, shell command,
PowerShell/CMD command, or arbitrary command line. Request bodies are limited to 16 KiB.

Legacy `/api/*` aliases remain temporarily but require the same Credential. New clients use
`/api/v1/*` exclusively.

