# Architecture

## Product boundary

Phone Remote transports control events from an authorized LAN client to a Windows PC. Display
transport is independent: the server contains no TV, HDMI, monitor, capture, video encoding,
or remote-desktop assumptions.

## Repository components

```text
Flutter Android/iOS client or Web fallback
          │ HTTPS API v1 + Bearer Credential
          ▼
phone_remote.api
  ├─ pairing/auth/state/security
  ├─ windows_control → Win32 input and explicit power operations
  ├─ app_launcher → configured app IDs only
  ├─ app_discovery/catalog → discover → user approve → expose
  └─ discovery → mDNS/DNS-SD announcement

Windows tray → loopback management API → clients/catalog/network/WoL diagnostics
```

The Flutter client separates UI from `DeviceRepository`, `DiscoveryService`, `ApiClient`,
`PairingService`, `RemoteSession`, `WakeService`, and secure/metadata storage. Device metadata stores
only a credential reference; Android Keystore/iOS Keychain-backed storage owns the credential.
`RealDeviceRepository` handles saved PCs while `DemoDeviceRepository` provides an explicit offline
review mode. Pointer moves are coalesced at a 33 ms cadence so stale raw events cannot create an
unbounded HTTP queue.

`protocol/openapi.yaml` is the Server/Mobile boundary. Product versions do not need to match;
API compatibility is tracked by `apiVersion=1`.

## Runtime state

Installed binaries belong in `C:\Program Files\Phone Remote`. Mutable state belongs to
`%LOCALAPPDATA%\PhoneRemote`:

```text
config.json
icons/
state.json
server-identity.key
server.crt
server.key
logs/
```

The ECDSA P-256 identity key is stable across certificate renewal. `state.json` contains server
metadata and one record per client, including only a salted scrypt verifier—not the plaintext
Credential. Updates use a same-directory temporary file plus atomic replacement.

## Process model

The HTTP server uses a bounded-request, threaded standard-library server. Control operations
are serialized by `ControlService` so concurrent clients are executed in server receive order
at the service boundary. The tray owns user-facing lifecycle actions; mDNS and HTTP are stopped
during shutdown. Windows-specific behavior is behind injectable classes for safe testing.

## Application trust transition

Providers read Start Menu shortcuts, uninstall metadata, App Paths, and MSIX Start Apps. Their
outputs are normalized and merged as `DiscoveredApp` candidates. Discovery never changes the
remote Catalog. Only an explicit local administrator approval creates a `ConfiguredApp`; only
configured and enabled IDs are returned to remote clients.
