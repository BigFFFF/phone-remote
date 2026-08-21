# Development

## Toolchain

- Windows 11, Python 3.12, Inno Setup 6
- Flutter 3.24.5 / Dart 3.5.4, JDK 17, Android API 36
- macOS with Xcode 16+ and CocoaPods 1.15+ for iOS builds

## Server

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\server[dev]"
Set-Location server
..\.venv\Scripts\ruff.exe format .
..\.venv\Scripts\ruff.exe check .
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

Use a temporary `PHONE_REMOTE_DATA_DIR` for experiments. Automated tests must use injected or mock
Windows-control backends rather than real power, firewall, registry, or launch actions.

## Mobile

From `mobile/`:

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Optional real Companion pairing test:

```powershell
$env:PHONE_REMOTE_LIVE_SERVER_TEST = "1"
$env:PHONE_REMOTE_PYTHON = "..\.venv\Scripts\python.exe"
flutter test test/live_server_integration_test.dart
```

## Windows build

```powershell
.\packaging\windows\build.ps1
.\packaging\windows\build.ps1 -Installer
```

Outputs are `dist\PhoneRemote.exe` and
`packaging\windows\dist\PhoneRemoteSetup.exe`.

## Change checklist

- Keep `config.json version=1` compatible unless a migration is included.
- Update `protocol/openapi.yaml` and tests when the API changes.
- Run the affected server or mobile checks before handing off a change.
