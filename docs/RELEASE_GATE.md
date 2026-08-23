# Release status

Status as of 2026-08-23.

## Implemented and locally tested

- API v1, identity, pairing, authentication, revocation, controls, and approved-app Catalog
- Tray management, Web Remote, mDNS, network policy, packaging scripts, and CI definitions
- Flutter onboarding, discovery, secure multi-PC storage, Remote controls, Demo mode, and Android WoL
- Android APK/AAB project structure and iOS project/resources
- GitHub `v1.3.0` direct-download packaging: signed Android APK and Windows Inno Setup installer
- In-place Android and Windows upgrades, single-file Companion configuration, and first-run
  Edge/Steam discovery
- Coalesced, sensitivity-adjustable native touch input and request-bounded Web Remote touch input
- Manually selectable Chinese/English UI across Windows management, tray, Web Remote, and mobile
- Steam launcher selection that rejects uninstall entries and repairs the legacy bad auto-selection

## Remaining acceptance work

- Windows installer matrix and real-PC control UX
- Physical Android LAN, control, and Wake on LAN testing
- macOS/Xcode and physical iPhone validation
- Windows Authenticode signing, store metadata, and store publication

See `STORE_RELEASE.md` for platform release gates. The Android APK is signed with the project's
locally retained release key. The Windows installer is not Authenticode-signed because no trusted
code-signing certificate is configured; no store approval or entitlement approval is claimed.
