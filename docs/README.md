# EWC Backend — Architecture & API Contract (Phase 1)

This directory contains the architecture design and API contract for
extracting all business logic from `ewccli` into a standalone backend
service.

## Documents

| Document | Description |
|---|---|
| [ADR-001-target-architecture.md](./ADR-001-target-architecture.md) | Architecture Decision Record covering backend framework, service layering, repository layout, deployment topology, CLI↔backend communication, and AI agent-friendly API design. |
| [auth-authorization-model.md](./auth-authorization-model.md) | Authentication & authorization model: CLI↔backend auth, agent authorization (OAuth2 client credentials + scoped API tokens), and OpenStack credential management/rotation (proposed secret store: OpenBao, with alternatives). Documents the current state (long-term credentials in plaintext files, no IdP) and the target model (Keycloak OIDC + OpenBao secret store, both proposed). |
| [job-execution-model.md](./job-execution-model.md) | Long-running job execution model: job lifecycle, submission, status, logs (polling + SSE), outputs, cancellation, timeouts, and retry/idempotency. |
| [openapi.yaml](./openapi.yaml) | OpenAPI 3.1 specification covering all current CLI capabilities. |

## CLI Capability Coverage

The OpenAPI spec maps every current `ewccli` capability to backend API
endpoints:

| CLI Command | API Endpoint | Sync/Async |
|---|---|---|
| `ewc login` | `POST /v1/auth/token` | Sync |
| `ewc infra create` | `POST /v1/servers` | Async |
| `ewc infra list` | `GET /v1/servers` | Sync |
| `ewc infra show` | `GET /v1/servers/{name}` | Sync |
| `ewc infra delete` | `DELETE /v1/servers/{name}` | Async |
| `ewc infra create --force` (reconfigure) | `POST /v1/servers/{name}/reconfigure` | Async |
| `ewc hub list` | `GET /v1/hub/items` | Sync |
| `ewc hub show` | `GET /v1/hub/items/{name}` | Sync |
| `ewc hub deploy` | `POST /v1/hub/items/{name}/deploy` | Async |
| keypair create (internal) | `POST /v1/keypairs` | Async |
| keypair delete (internal) | `DELETE /v1/keypairs/{name}` | Async |
| `ewc dns create` | `POST /v1/dns/records` | Async |
| `ewc dns get` | `GET /v1/dns/records` | Sync |
| `ewc dns describe` | `GET /v1/dns/records/{name}` | Sync |
| `ewc dns delete` | `DELETE /v1/dns/records/{name}` | Async |
| `ewc s3 bucket create` | `POST /v1/s3/buckets` | Async |
| `ewc s3 bucket get` | `GET /v1/s3/buckets` | Sync |
| `ewc s3 bucket delete` | `DELETE /v1/s3/buckets/{name}` | Async |
