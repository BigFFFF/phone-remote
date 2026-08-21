# Phone Remote protocol

[`openapi.yaml`](openapi.yaml) is the API v1 source of truth. Native clients use identity-pinned
HTTPS; Web Remote uses plaintext HTTP only on a trusted Private LAN. Pairing routes are public and
control routes require a per-client Bearer Credential.

Remote app launches accept only locally approved application IDs. The loopback-only management API
is outside this contract.
