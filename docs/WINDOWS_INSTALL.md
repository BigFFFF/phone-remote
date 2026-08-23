# Windows installation

Build the installer from a Python 3.12 checkout:

```powershell
.\packaging\windows\build.ps1 -Installer
```

Output: `packaging\windows\dist\PhoneRemoteSetup.exe`.

## Installer behavior

- Installs Companion under Program Files and runs it as the current user.
- Creates optional shortcuts and per-user startup registration.
- Adds program-specific `Private` + `LocalSubnet` rules for TCP 8765/8766 and UDP 5353.
- Supports in-place upgrades; uninstall removes startup/firewall entries but preserves user data
  unless full cleanup is selected.
- Stores runtime configuration in `%LOCALAPPDATA%\PhoneRemote\config.json`.

On first startup, Companion finds Edge and the real Steam launcher, then adds installed matches to
the approved application list.

Before release, validate install, upgrade, firewall repair, startup, uninstall/reinstall, cleanup,
Private-LAN access, and Public-network blocking on a disposable account or VM.

Wake on LAN also depends on firmware, NIC driver, Magic Packet, and power-management settings.
