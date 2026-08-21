# Phone Remote privacy policy

Last updated: 2026-08-21

Phone Remote communicates directly over the user's local network. It has no Phone Remote cloud
account, ads, analytics SDK, third-party telemetry, or control-history upload.

## Local data

Windows Companion stores configuration, Server Identity and TLS material, paired-device records,
salted Credential verifiers, approved applications, and rotating operational logs in Local
AppData. Mobile stores paired-PC metadata and settings locally; Credentials use Android
Keystore/iOS Keychain-backed storage.

Logs may include client IDs, connection or pairing results, action types, approved app IDs, and
errors. They are not intended to contain Credentials, pairing codes, keyboard text, passwords, or
raw sensitive request bodies.

## Retention and deletion

Pairings remain until revoked or user data is deleted. Windows uninstall preserves user data by
default and offers explicit full cleanup. Old logs are removed by rotation.

Privacy questions should use the repository owner's contact channel without attaching secrets or
raw state files. This policy must be updated before any material data-handling change is released.
