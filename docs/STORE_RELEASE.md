# Store and release gates

This file records external gates; it is not evidence that any account, signing key, entitlement,
or store approval exists.

## Windows

- Code-signing certificate and signed installer: pending external credential
- SmartScreen reputation: pending signed distribution
- Installer VM matrix and RC acceptance: pending final RC execution
- GitHub Release publication: manual and not performed automatically

## Android

The Flutter project, Keystore-backed credential storage, native UI, Android WoL, API 36 build
configuration, debug APK, and unsigned Release APK/AAB structure are implemented. Remaining gates
are a real signing key, signed AAB, physical-device LAN/control/WoL matrix, Play Console listing,
privacy forms, and internal testing. At release time re-check current Google Play target API and
signing requirements rather than relying on a dated plan statement.

## iOS

The Flutter/iOS project, Keychain-backed credential storage, Bonjour declarations, local-network
privacy string, shared native UI, and graceful unavailable Wake capability are implemented in
source. Xcode no-sign compilation, physical-device validation, signing, TestFlight, and App Store
metadata remain. Formal build/archive/signing requires macOS, Xcode 16+ (or the then-current
supported baseline), and CocoaPods. Multicast networking entitlement must be requested from Apple
if a future iOS WoL implementation requires it; no approval is claimed.

## Production control

No workflow in this repository publishes a Production store release. Windows, Play, TestFlight,
and App Store publication retain a final manual confirmation.
