# Phone Remote privacy policy

Last updated: 2026-08-20

Phone Remote operates between devices on the user's local network. It has no Phone Remote cloud
account, advertising, analytics SDK, third-party telemetry, or control-history upload.

## Data stored locally

Windows Companion stores Server Identity material, TLS keys/certificate, paired-device metadata,
salted Credential verifiers, configuration, application Catalog, and rotating operational logs in
the Windows user's Local AppData directory. A future mobile app will store paired-PC metadata,
settings, and Credentials locally, with Credentials protected by Android Keystore or iOS Keychain.

Logs may include client ID, connect/pair results, action type, configured app ID, and errors. They
do not intentionally record Bearer Credentials, pairing codes, keyboard text, passwords, or raw
sensitive request bodies.

## Network use and sharing

The product exchanges discovery, pairing, status, and remote-control messages directly over the
local network. It does not send this data to the project owner or sell/share it with advertisers or
data brokers. Users should not expose Companion to the public internet.

## Retention and deletion

Pairing records remain until the user removes a device, revokes all devices, or explicitly deletes
Phone Remote user data. Uninstall preserves settings by default for reinstall continuity and offers
an explicit full-cleanup choice. Log rotation removes older log files automatically; users may also
delete the local logs while Companion is stopped.

## Contact and changes

Use the repository's owner contact channel for privacy questions without attaching secret keys,
Credentials, pairing codes, keyboard content, or raw state files. Material behavior changes must
be reflected in this policy before release.

