# Phone Remote

[简体中文](README.md) | English

## About

Phone Remote is a Windows remote-control toolkit designed for trusted local networks. It includes a
Windows Companion, a Flutter mobile app, and an installation-free Web Remote. A phone, tablet, or
browser can act as a touchpad, keyboard, D-pad, media remote, and application launcher, with
additional controls for standby, hibernation, restart, shutdown, and Wake on LAN.

It is useful for controlling a PC from a couch or bed, managing living-room media, advancing
presentations, launching applications such as Steam from across the room, and handling everyday
tasks when a physical mouse and keyboard are inconvenient. Everything stays on the local network,
with no cloud account required and no need to expose the PC to the internet.

## Download the Stable Release

- [Windows installer](https://github.com/BigFFFF/phone-remote/releases/latest/download/PhoneRemoteSetup-v1.3.0.exe)
- [Android APK](https://github.com/BigFFFF/phone-remote/releases/latest/download/PhoneRemote-v1.3.0-android.apk)
- [Release notes and checksums](https://github.com/BigFFFF/phone-remote/releases/latest)

The Windows and Android devices must be connected to the same trusted local network. On the first
connection, enter the pairing code displayed by the Windows tray application.

## Features

- Pair once and retain trust, with independent management for multiple phones and PCs
- Touchpad, D-pad, keyboard, media, application-launching, and power controls
- Automatic discovery through mDNS, with manual address entry as a fallback
- Manual Wake on LAN on Android, with safe capability fallback on iOS
- Adjustable and persistent touchpad pointer and scrolling sensitivity
- Automatic discovery of installed Edge and Steam applications on first Windows launch
- Double-click the Windows tray icon to open Applications, where startup, pairing, and application settings are centralized
- Manually select Chinese or English in the Windows client, Web Remote, and mobile app
- Standby, hibernation, restart, and shutdown controls
- HTTPS with a pinned Server Identity in the native app
- Web Remote support for standard browsers on trusted private networks

## Project Structure

```text
server/                 Windows Companion, management page, and Web Remote
mobile/                 Flutter Android/iOS app
protocol/openapi.yaml   Single machine-readable contract for API v1
packaging/windows/      Windows packaging and installer
docs/                   Design, development, security, and release documentation
```

## Run the Companion from Source

Windows 11 and Python 3.12 are required:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\server[dev]"
.\.venv\Scripts\python.exe -m phone_remote
```

Application data is stored in `%LOCALAPPDATA%\PhoneRemote` by default. The tray menu can open the
management page, display the pairing code, and copy the Web Remote address. To run in development
mode without the tray icon:

```powershell
.\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

## Development Resources

- [Development and testing](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Protocol overview](docs/PROTOCOL.md)
- [Security boundaries](docs/SECURITY.md)
- [Windows installation](docs/WINDOWS_INSTALL.md)
- [Web Remote guide](docs/WEB_REMOTE.md)
- [Release status](docs/RELEASE_GATE.md)

This project is intended for local networks only. Do not expose it to the internet through port
forwarding, public firewall rules, or cloud tunnels. Web Remote uses unencrypted HTTP and should
only be used on a trusted private network.
