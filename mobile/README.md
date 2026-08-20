# Phone Remote Mobile

Flutter 3.24.5 Android/iOS client for the Phone Remote API v1. The app has native onboarding,
mDNS/manual discovery, pinned TLS identity pairing, multi-PC storage, secure per-PC credentials,
Touchpad-first remote controls, approved apps, power controls, Android Wake on LAN, and an explicit
offline Demo mode.

## Toolchain

- Flutter 3.24.5 / Dart 3.5.4
- JDK 17
- Android SDK API 36, Build Tools 36.0.0 and compatibility Build Tools 33.0.1
- Xcode 16+ and CocoaPods 1.15+ for iOS builds

From `mobile/`:

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

For a development machine in mainland China, the mirrors are opt-in and do not affect CI or other
developers:

```powershell
$env:PUB_HOSTED_URL = "https://pub.flutter-io.cn"
$env:FLUTTER_STORAGE_BASE_URL = "https://storage.flutter-io.cn"
$env:PHONE_REMOTE_CHINA_MIRRORS = "true"
flutter pub get
flutter build apk --debug
```

`PHONE_REMOTE_CHINA_MIRRORS=true` enables Aliyun Google/Public Maven mirrors before the official
repositories. Official repositories remain configured as fallback.

## Live HTTPS integration

The normal test suite is self-contained. A separate opt-in test starts the real Python Companion in
a temporary data directory, pairs over self-signed HTTPS, verifies the stable ECDSA identity, stores
the credential separately, and reconnects with Bearer authentication:

```powershell
$env:PHONE_REMOTE_LIVE_SERVER_TEST = "1"
$env:PHONE_REMOTE_PYTHON = "..\.venv\Scripts\python.exe"
flutter test test/live_server_integration_test.dart
```

The integration test performs no keyboard, mouse, power, app-launch, firewall, or installer action.

## Security

Device metadata contains only a credential reference. Android Keystore/iOS Keychain-backed storage
holds the credential. A changed server public-key fingerprint blocks reconnect. Never commit signing
keystores or `key.properties`/`keystore.properties`.
