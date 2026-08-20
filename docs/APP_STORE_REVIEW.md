# App Store review preparation

The native Flutter mobile application now exists for Android and iOS. Source/widget validation is
complete on Windows; physical iPhone UX, macOS/Xcode compilation, signing, entitlement, TestFlight,
and App Store review remain external gates.

The current app provides native Flutter onboarding, device management, pairing, Remote with
Touchpad as the default mode, optional D-pad, keyboard quick access, Media, Apps, Power, and Demo
Mode. These flows still require final physical-device acceptance. Web Fallback is not a substitute
for the native product UI.

Demo Mode must avoid LAN access while demonstrating remote interactions, apps, media, power
confirmation, and online/offline states, with a visible `Demo` label. Review notes should explain
that the app controls a user-owned Windows PC on the same LAN, needs Windows Companion for live
mode, collects no keyboard content, uses no cloud account, and offers Demo Mode to reviewers.

Before submission, verify current Apple review rules, local-network privacy requirements,
Bonjour service declarations, multicast entitlement status, privacy nutrition labels, screenshots,
support URL, and reviewer instructions. Do not state that restricted entitlement approval exists
until Apple has actually granted it.
