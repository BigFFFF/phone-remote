# Windows installation

## Build stages

```text
python -m phone_remote
        ↓ PyInstaller
PhoneRemote.exe
        ↓ Inno Setup 6
PhoneRemoteSetup.exe
```

Run `packaging\windows\build.ps1 -Installer` from a Python 3.12 development checkout. The final
acceptance artifact is the installer, not merely source or the standalone executable.

## Installer behavior

The installer requests elevation once, installs under Program Files, creates Start Menu and
optional Desktop shortcuts, optionally registers per-user startup, and starts Companion as the
original non-elevated user. Daily operation does not require UAC.

It owns exactly two inbound rules:

- TCP 8765, program-specific, Private profile, `LocalSubnet`
- UDP 5353, program-specific, Private profile, `LocalSubnet`, for mDNS

Upgrade removes and repairs only these named rules. Uninstall stops the process, removes its
startup registration and rules, and removes Program Files. It preserves
`%LOCALAPPDATA%\PhoneRemote` by default so Identity and pairings survive reinstall. An explicit
uninstall prompt offers full user-data cleanup.

The installer never disables Windows Firewall, changes global policy, marks Public networks as
Private, creates an outbound-any rule, modifies another program's rule, changes a router, uses
UPnP, or configures public port forwarding.

## Migration

At first run, Companion copies an old adjacent `config.json` and missing adjacent icons only when
the destination under Local AppData does not already exist. It never overwrites an existing user
configuration. `state.json`, identity keys, certificates, and pairings remain entirely in the
user-data directory.

## Acceptance checklist

Validate fresh install, old config migration, upgrade, identity and pairing retention, firewall
repair, startup, uninstall, reinstall, default settings retention, opt-in full cleanup, Private
LocalSubnet access, and Public-profile blocking on a disposable Windows test account or VM.
Power actions must never be exercised by CI.

## Wake on LAN

Companion reports physical adapters and MAC addresses. Wake readiness also depends on firmware,
NIC driver, Magic Packet settings, and device power management. The current diagnostic does not
claim that unsupported firmware or driver settings were changed successfully.

