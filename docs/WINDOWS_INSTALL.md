# Windows installation

Build the installer from a Python 3.12 checkout:

```powershell
.\packaging\windows\build.ps1 -Installer
```

The output is `packaging\windows\dist\PhoneRemoteSetup.exe`.

## Installer behavior

- Installs Companion under Program Files and runs it as the normal user.
- Creates optional shortcuts and per-user startup registration.
- Adds program-specific `Private` + `LocalSubnet` rules for TCP 8765/8766 and UDP 5353.
- Removes its startup entry and firewall rules on uninstall.
- Preserves `%LOCALAPPDATA%\PhoneRemote` by default; full cleanup is an explicit uninstall choice.

First run may migrate a legacy adjacent `config.json` and missing icons, but never overwrites
existing Local AppData state.

Before release, validate fresh install, upgrade, firewall repair, startup, uninstall/reinstall,
state retention, optional cleanup, Private-LAN access, and Public-network blocking on a disposable
Windows account or VM.

Wake on LAN also depends on firmware, NIC driver, Magic Packet, and power-management settings.
