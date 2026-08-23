# Security

## Boundary

Phone Remote is LAN-only and cannot defend a compromised Windows account. Native clients may use
untrusted LANs; Web Remote requires a trusted LAN because its traffic is plaintext.

## Invariants

- Native control uses HTTPS and pins a stable ECDSA P-256 Server Identity.
- Pairing codes are random, single-use, short-lived, rate-limited, and never logged.
- Every client receives an independent 256-bit credential; Windows stores only a salted scrypt
  verifier and mobile stores the secret through platform secure storage.
- Missing, invalid, or revoked credentials cannot use protected routes.
- Remote clients can launch only locally approved application IDs, never paths or commands.
- Request sizes and values are validated; keyboard text and credentials are not logged.
- Management APIs require loopback access and an ephemeral process token.
- Installer firewall rules are program-specific, Private-profile, and `LocalSubnet` only; runtime
  checks also block non-loopback access on Public networks.

## Web Remote

HTTP 8766 can expose credentials, keyboard text, and commands on the LAN. Use it only on a trusted
private network; otherwise use the native app.

## Operations

Never expose ports 8765/8766 through NAT, UPnP, public firewall rules, or cloud tunnels. Preserve
`%LOCALAPPDATA%\PhoneRemote` when migrating pairings. Resetting identity requires deleting user
data and pairing again.

Security reports should not include credentials, keys, pairing codes, keyboard text, or raw state
files.
