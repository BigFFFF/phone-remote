# Security

## Boundary

Phone Remote is LAN-only and does not defend a compromised Windows account. Native clients may run
on an untrusted LAN; Web Remote assumes the LAN itself is trusted because its traffic is plaintext.

## Invariants

- Native control uses HTTPS and pins a stable ECDSA P-256 Server Identity.
- Pairing codes are random, single-use, short-lived, rate-limited, and never logged.
- Every client receives an independent 256-bit Credential; Windows stores only a salted scrypt
  verifier and mobile stores the secret through platform secure storage.
- Missing, invalid, or revoked credentials cannot use protected routes.
- Remote clients can launch only locally approved application IDs, never paths or commands.
- Request sizes and values are validated; keyboard text and credentials are not logged.
- Management APIs require loopback access and an ephemeral process token.
- Installer firewall rules are program-specific, Private-profile, and `LocalSubnet` only; runtime
  checks also block non-loopback access on Public networks.

## Web Remote

HTTP 8766 can expose credentials, keyboard text, and commands to another device on the same LAN.
Use it only on a trusted private network; prefer the native App elsewhere.

## Operations

Do not expose ports 8765/8766 through NAT, UPnP, public firewall rules, or cloud tunnels. Preserve
`%LOCALAPPDATA%\PhoneRemote` when migrating trusted pairings. An intentional identity reset requires
deleting user data and pairing clients again.

Security reports should not include credentials, keys, pairing codes, keyboard text, or raw state
files.
