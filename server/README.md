# Windows Companion server

The server is a Python 3.12 Windows application with an HTTPS API, persistent identity,
independent paired-client credentials, mDNS discovery, a tray entry point, loopback-only
management UI, and an authenticated web fallback remote.

Run `python -m phone_remote`; use `--help` for development switches. Production builds must
not use `--insecure-http`. Tests inject Windows-control backends and never execute real power,
firewall, destructive registry, or application-launch operations.

See the repository-level `README.md` and `docs/DEVELOPMENT.md` for setup commands.
