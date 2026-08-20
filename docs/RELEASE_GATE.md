# Release gate report

Status as of 2026-08-20. `Complete` means implemented in source and covered by local tests;
installer/real-device items remain separate acceptance gates.

| Area | Status | Evidence / remaining gate |
| --- | --- | --- |
| Python monorepo server | Complete | `server/phone_remote`, Python 3.12 |
| API v1 and OpenAPI | Complete | `protocol/openapi.yaml`, API tests |
| Persistent Identity/TLS | Complete | ECDSA P-256 identity, certificate persistence tests |
| Pairing/auth/multi-client | Complete | independent hash records, rate/expiry/revocation tests |
| Windows controls | Complete in source | mocked tests; real-PC UX acceptance remains |
| Application discovery/Catalog | Complete in source | four providers, approval gate, missing detection tests |
| Tray/local management/Web Fallback | Complete in source | manual UI acceptance remains |
| mDNS/network/firewall support | Complete in source | Private/LocalSubnet command tests; VM acceptance remains |
| PyInstaller executable | Built | local `PhoneRemote.exe --smoke-test` passed; unsigned |
| Inno Setup installer | Built | `PhoneRemoteSetup.exe` compiled; fresh/upgrade/uninstall VM matrix remains |
| Server CI | Complete in source | first GitHub run remains external |
| Flutter core architecture | Complete in source | native onboarding, discovery, pairing, secure multi-PC storage, reconnect and Demo |
| Flutter remote controls | Complete in source | Touchpad throttling, D-pad, keyboard, media, approved apps and guarded power UI; real-phone UX acceptance remains |
| Android/WoL | Debug APK built | API 36 build passed; physical-device LAN/WoL and signed AAB remain |
| iOS | Project ready in source | Keychain storage and graceful unavailable Wake capability; macOS/Xcode no-sign CI run remains |
| Mobile CI | Complete in source | Android analyze/test/APK plus macOS iOS no-sign workflow; first hosted run remains external |
| Store signing/accounts/entitlements | External | see `STORE_RELEASE.md` |

No release, store upload, developer-account creation, signing, or entitlement request was
performed automatically.
