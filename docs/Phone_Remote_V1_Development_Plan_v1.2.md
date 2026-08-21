# Phone Remote V1 status

This file replaces the completed historical implementation plan. It is a status summary, not a
second specification.

## Current baseline

Phone Remote is a monorepo containing a Windows Companion, Flutter Android/iOS app, browser Web
Remote, API v1 contract, Windows installer project, and CI workflows. Core source implementation
and local automated tests are complete.

## Sources of truth

- Product entry point: `README.md`
- Architecture: `docs/ARCHITECTURE.md`
- API: `protocol/openapi.yaml`
- Security boundary: `docs/SECURITY.md`
- Development commands: `docs/DEVELOPMENT.md`
- Release readiness: `docs/RELEASE_GATE.md`

## Remaining work

1. Run the Windows installer acceptance matrix on a clean VM.
2. Validate Android behavior and Wake on LAN on physical devices.
3. Build and validate iOS on macOS and a physical iPhone.
4. Complete signing, hosted CI confirmation, store metadata, and manual publication.

New work should update the relevant source of truth rather than expanding this file into another
requirement list.
