# Store and release gates

Source readiness does not imply signing, store approval, or publication.

| Platform | Remaining manual work |
| --- | --- |
| Windows | Obtain a trusted Authenticode certificate and run the clean-VM install/upgrade/uninstall matrix |
| Android | Sign AAB, test LAN/control/WoL on physical devices, complete Play listing and privacy forms |
| iOS | Build on current supported Xcode, test physical devices, sign, prepare TestFlight/App Store metadata |

GitHub `v1.3.0` provides a signed Android APK and an unsigned Windows installer for direct download.
The Android release key is retained locally and excluded from version control. Store publication is a
separate gate from this direct-download release.

Re-check current store SDK, signing, privacy, and entitlement requirements at submission time.
Request Apple multicast entitlement only if the shipping iOS Wake implementation needs it; no
approval is currently claimed.

Production publication always requires a final manual decision.
