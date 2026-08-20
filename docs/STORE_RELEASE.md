# Store and release gates

This file records external gates; it is not evidence that any account, signing key, entitlement,
or store approval exists.

## Windows

- Code-signing certificate and signed installer: pending external credential
- SmartScreen reputation: pending signed distribution
- Installer VM matrix and RC acceptance: pending final RC execution
- GitHub Release publication: manual and not performed automatically

## Android (deferred on this computer)

The Flutter project, secure storage, native UI, Android WoL, API 36 build configuration, signing,
AAB, Play Console listing, privacy forms, and internal testing are not implemented here. At
release time re-check current Google Play target API and signing requirements rather than relying
on a dated plan statement.

## iOS (deferred on this computer)

The Flutter/iOS project, Keychain storage, Bonjour declarations, local-network privacy strings,
Wake capability abstraction, Xcode build, signing, TestFlight, and App Store metadata remain.
Formal build/archive/signing requires macOS, Xcode 16+ (or the then-current supported baseline),
and CocoaPods. Multicast networking entitlement must be requested from Apple if the final WoL
implementation requires it; no approval is claimed.

## Production control

No workflow in this repository publishes a Production store release. Windows, Play, TestFlight,
and App Store publication retain a final manual confirmation.

