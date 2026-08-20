# Phone Remote protocol

`openapi.yaml` is the source of truth for API v1. Server and mobile product versions may
evolve independently while they both support API version `1`.

The protocol is LAN-only and HTTPS-only in production. `/info` and the two pairing routes
are public; all control routes require the independent Bearer credential issued to one
client during pairing. A client must retain the `serverId` and `identityFingerprint`, reject
an unexpected identity change, and store its credential in platform secure storage.

The server never accepts an executable path, URL, command line, or shell command from a
remote client. Application launch requests contain only a configured application ID.

The management API is deliberately excluded from this contract. It is loopback-only,
protected by an ephemeral process token, and used by Windows Companion rather than mobile
clients.

