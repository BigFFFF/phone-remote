# Development

## Fixed toolchain

- Windows 11
- Python 3.12.x in repository `.venv`
- pip 24 or newer, pytest 8+, Ruff 0.5+, PyInstaller 6+
- Inno Setup 6.x for the final installer
- Flutter 3.24.5 / Dart 3.5.4
- JDK 17, Android API 36, Build Tools 36.0.0 and 33.0.1
- Xcode 16+ and CocoaPods 1.15+ for iOS compilation

Do not use an unpinned global Python or `latest` in CI. The Server workflow fixes Python to 3.12.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\server[dev]"
```

## Local loop

```powershell
Set-Location server
..\.venv\Scripts\ruff.exe format .
..\.venv\Scripts\ruff.exe check .
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

Use a temporary `PHONE_REMOTE_DATA_DIR` for manual experiments. Never point tests at a real user
data directory. Windows control, power, process launch, Registry mutation, firewall mutation,
and installer effects must be mocked in automated tests.

## Module map

- `api.py`: HTTP routing, validation, authentication, static Web Client
- `security.py`, `state.py`, `auth.py`, `pairing.py`: identity and trust lifecycle
- `windows_control.py`, `app_launcher.py`: explicit Windows-side actions
- `app_discovery/`, `catalog.py`: untrusted candidates and approved Catalog
- `discovery.py`, `network.py`: mDNS, profiles, firewall/startup/WoL support
- `tray.py`, `server.py`: Companion UI and lifecycle

## Build

```powershell
.\packaging\windows\build.ps1
.\packaging\windows\build.ps1 -Installer
```

PyInstaller output is `dist\PhoneRemote.exe`; Inno Setup output is
`packaging\windows\dist\PhoneRemoteSetup.exe`. Build output is ignored by Git. Signing is a
release gate and is not simulated.

## Flutter mobile

From `mobile/`:

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Mainland China mirrors are opt-in. Set `PUB_HOSTED_URL=https://pub.flutter-io.cn`,
`FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn`, and
`PHONE_REMOTE_CHINA_MIRRORS=true`. The last variable enables Aliyun Maven mirrors while retaining
official repositories as fallback. CI does not set it.

Run the opt-in Python/Flutter HTTPS pairing and reconnect integration from `mobile/` with:

```powershell
$env:PHONE_REMOTE_LIVE_SERVER_TEST = "1"
$env:PHONE_REMOTE_PYTHON = "..\.venv\Scripts\python.exe"
flutter test test/live_server_integration_test.dart
```

The test uses a temporary Companion data directory and performs no remote-control or system action.
Windows cannot compile iOS; the Mobile CI macOS job performs a no-sign feasibility build.

## Change policy

Maintain `config.json version=1` compatibility. Do not remove a legacy path until the Web Client
and tests cover the v1 replacement. Update `protocol/openapi.yaml` with API changes and add tests
for authentication, bounds, error mapping, and command construction.
