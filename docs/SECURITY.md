# Security

## Threat model

Phone Remote assumes an untrusted device may join the same LAN. Merely reaching TCP port 8765
does not grant control. It does not defend a fully compromised Windows user account, and it is
not designed for public-internet exposure.

## Controls

- Production API is HTTPS with a locally generated ECDSA P-256 identity and certificate.
- The Flutter client hashes the exact DER SubjectPublicKeyInfo from the peer certificate, compares
  it with the advertised stable Server Identity, and pins it for every trusted reconnect. A changed
  identity blocks control instead of falling back to broad self-signed certificate trust.
- Pairing codes use the operating-system CSPRNG, expire in five minutes, are one-time, and are
  never returned to a LAN requester or written to logs.
- Client secrets contain at least 256 bits of entropy. Only a salted scrypt verifier is stored;
  verification uses constant-time comparison.
- Credentials are independent and independently revocable. Revoke All invalidates every active
  client without rebuilding the Server Identity.
- Mobile device metadata stores only a credential reference. The plaintext Credential is delegated
  to Android Keystore/iOS Keychain-backed secure storage and is never written to shared preferences.
- Non-public routes return 401 for missing, invalid, or revoked Credentials.
- The body limit is 16 KiB; malformed JSON, invalid values, NaN/Infinity, oversized text,
  traversal, unknown actions, and unknown apps are rejected.
- Application launches use argument arrays with `shell=False`. Remote clients supply only an
  approved ID. Discovery candidates are never auto-trusted.
- Installer firewall rules are program-, protocol-, port-, Private-profile-, and
  LocalSubnet-specific. The server also refuses non-loopback requests when only Public networks
  are active.
- Management routes require loopback plus an ephemeral 256-bit process token carried in the URL
  fragment from the tray; the fragment is not sent as an HTTP referrer.

## Logging

Rotating INFO logs may contain a client ID, pairing success/failure, action type, app ID, network
status, and errors. They must not contain a Bearer Credential, pairing code, keyboard text,
password, or raw sensitive request body. Tests assert this for keyboard input and credentials.

## Operational guidance

Do not expose the port through NAT, UPnP, router forwarding, a public firewall profile, or a
cloud tunnel. Back up `%LOCALAPPDATA%\PhoneRemote` if preserving pairings during OS migration.
If an identity key is unexpectedly replaced, the server stops instead of silently trusting it.
To intentionally reset trust, remove user data through the explicit uninstall choice and pair
all clients again.

Report security defects privately to the repository owner; do not include Credentials, keys,
pairing codes, keyboard text, or a raw `state.json` in a report.
