# Release status

Status as of 2026-08-25: GitHub `v1.4.0` is published with a signed Android APK and an unsigned
Windows installer.

## Ready

- API v1, identity, pairing, revocation, controls, approved applications, mDNS, and network policy
- Windows tray/management UI, Web Remote, installer, in-place upgrades, and Edge/Steam discovery
- Flutter discovery, secure multi-PC storage, controls, Demo mode, Android WoL, and signed APK/AAB
- Manual Chinese/English selection across Windows, Web Remote, and mobile
- Server and mobile CI, automated tests, and direct-download packaging

## Platform gates

| Platform | Remaining manual work |
| --- | --- |
| Windows | Obtain an Authenticode certificate; test clean install, upgrade, uninstall, firewall, and real-PC controls |
| Android | Test LAN/control/WoL on physical devices; finish Play listing, privacy forms, and publication |
| iOS | Build and sign with current Xcode; test a physical iPhone; prepare TestFlight/App Store metadata |

For App Store review, mention the Companion requirement, local-network discovery, offline Demo
mode, and the absence of cloud accounts, ads, analytics, or keyboard-content collection. Request an
Apple network entitlement only if the final iOS implementation requires it.

Store publication remains separate from the GitHub release and requires a final manual decision.
Re-check current SDK, signing, privacy, entitlement, and store requirements before submission.
