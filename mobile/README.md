# Phone Remote Mobile

Flutter 3.24.5 Android/iOS client for API v1. It provides discovery, identity-pinned pairing,
secure multi-PC storage, configurable Touchpad/D-pad controls, keyboard, media, approved apps,
standby/hibernate/restart/shutdown controls, explicit Android Wake on LAN, and offline Demo mode.

## Develop

Requirements: Flutter 3.24.5, JDK 17, Android API 36. iOS builds require macOS, Xcode 16+, and
CocoaPods 1.15+.

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Optional real Companion integration test:

```powershell
$env:PHONE_REMOTE_LIVE_SERVER_TEST = "1"
$env:PHONE_REMOTE_PYTHON = "..\.venv\Scripts\python.exe"
flutter test test/live_server_integration_test.dart
```

For mainland China development only, set `PUB_HOSTED_URL=https://pub.flutter-io.cn`,
`FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn`, and
`PHONE_REMOTE_CHINA_MIRRORS=true` before dependency or build commands.

Credentials are stored through Android Keystore/iOS Keychain-backed storage. Do not commit signing
keys or keystore configuration. Branding masters live under `assets/branding/`.
