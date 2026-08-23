# Phone Remote privacy policy

Last updated: 2026-08-21

Phone Remote communicates directly over the user's local network. It has no Phone Remote cloud
account, ads, analytics SDK, third-party telemetry, or control-history upload.

## Local data

Windows Companion stores configuration, identity/TLS material, paired devices, salted credential
verifiers, approved applications, and rotating logs in Local AppData. Mobile stores paired-PC
metadata and settings locally; credentials use Android Keystore/iOS Keychain-backed storage.

Logs may include client IDs, connection results, action types, approved app IDs, and errors. They
must not contain credentials, pairing codes, keyboard text, passwords, or sensitive request bodies.

## Retention and deletion

Pairings remain until revoked or user data is deleted. Windows uninstall preserves user data by
default and offers explicit full cleanup. Old logs are removed by rotation.

Send privacy questions through the repository owner's contact channel without attaching secrets or
raw state files. Update this policy before releasing any material data-handling change.
