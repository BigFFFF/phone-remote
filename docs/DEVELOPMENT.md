# Development

## Toolchain

- Windows 11, Python 3.12, Inno Setup 6
- Flutter 3.47.1 / Dart 3.13.1, Eclipse Temurin JDK 21, Android API 36
- Android Gradle Plugin 9.1.0 / Gradle 9.3.1, Java and Kotlin target 21
- macOS with Xcode 16+ and CocoaPods 1.15+ for iOS builds

## Server

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c .\server\constraints.txt -e ".\server[dev]"
Set-Location server
..\.venv\Scripts\ruff.exe format .
..\.venv\Scripts\ruff.exe check .
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

Use a temporary `PHONE_REMOTE_DATA_DIR` for experiments. Tests must mock Windows power, firewall,
registry, and launch actions.

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

Outputs: `dist\PhoneRemote.exe` and `packaging\windows\dist\PhoneRemoteSetup.exe`.

## Change checklist

- Run `python tools/sync_version.py` after changing `VERSION`; use `--write` to update references.
- Target the current data and API formats; compatibility migrations are not required.
- Update `protocol/openapi.yaml` and tests with API changes.
- Run affected checks before handoff.
