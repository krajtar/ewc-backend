# ADR-001: ewc-backend Target Architecture

| Field | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-07-03 |
| **Decision Owner** | EWC Platform Team |
| **Related Issue** | KAM-6 |
| **Supersedes** | — |

---

## 1. Context

`ewccli` is a Python CLI tool that manages European Weather Cloud (EWC)
infrastructure: OpenStack VMs, Kubernetes CRDs (DNS records, S3 buckets),
hub-item deployments (Ansible playbooks), and authentication flows.

### Current state (as-is)

Today the CLI holds **long-term** OpenStack application credentials in
**files on the user's local disk** (`~/.ewccli/profiles`,
plaintext INI). The user obtains application credentials manually from
the EWC web portal and provides them directly to `ewc login` (via CLI
arguments, environment variables, interactive prompts, or
`~/.config/openstack/clouds.yaml`). There is no identity provider, no
OIDC, and no token ceremony. The CLI persists the credentials to disk
and, on every subsequent command, reads them and calls
OpenStack/Kubernetes **directly** — there is no backend.

> An **OpenBao JWT login** path was explored as an experiment but is
> **not** part of the production CLI and is **not** how any user
> authenticates today. It is relevant here only as prior art for the
> *target* secret-store decision (§2.4); it must not be read as the
> current production behaviour.

All business logic — OpenStack SDK calls, Ansible execution, Kubernetes
CRD management, credential handling — lives inside the CLI process. This
creates several problems:

1. **Credential exposure.** Long-term OpenStack application credentials are
   stored on the user's local disk (`~/.ewccli/profiles`) in plaintext and
   persist between sessions. Rotation requires every user to re-run
   `ewc login`.
2. **No shared state.** Long-running deployments (VM creation + Ansible
   provisioning, DNS resolution waits up to 20 min) block the terminal. If
   the CLI is interrupted, the operation is lost with no recovery path.
3. **Duplicated logic for every consumer.** Any automation, CI pipeline, or
   future web UI must reimplement the same orchestration logic that the CLI
   currently holds, or shell out to the CLI.
4. **Not agent-friendly.** AI agents cannot reliably drive a Rich/Click
   terminal UI; they need structured, predictable HTTP endpoints with
   machine-readable schemas and error codes.

This ADR defines the target architecture for extracting all business logic
into a standalone **`ewc-backend`** service, with `ewccli` becoming a thin
client that calls the backend API.

---

## 2. Decision

### 2.1 Backend Framework: FastAPI

**Decision:** Use **FastAPI** as the backend web framework.

**Rationale:**
- The ewccli project already depends on **pydantic 2.x**; FastAPI is built
  on pydantic, so data models can be shared or mirrored without a schema
  translation layer.
- FastAPI generates an OpenAPI 3.x spec automatically from route
  definitions and pydantic models — the spec in this repository is the
  contract that both the CLI and AI agents consume.
- Native `async`/`await` support is essential for long-running operations
  (VM provisioning, Ansible runs, DNS polling) that must not block the
  event loop.
- First-class dependency injection (FastAPI `Depends`) maps cleanly to the
  service-layering model (§2.2).
- Broad ecosystem: Uvicorn/Starlette, Pydantic v2, SQLAlchemy async,
  structured logging, OpenTelemetry instrumentation.

**Alternatives considered:**
- *Flask*: synchronous by default; no built-in OpenAPI generation; would
  require additional libraries (flask-smorest, apispec) to reach parity.
- *Django REST Framework*: heavier; ORM coupling; less natural fit for a
  stateless API service.
- *aiohttp*: capable but smaller ecosystem; no automatic schema generation.

### 2.2 Service Layering

**Decision:** Three-layer architecture: **API → Service → Backend Clients**.

```
┌──────────────────────────────────────────────────────┐
│                   ewc-backend                         │
│                                                      │
│  ┌────────────┐   ┌──────────────┐   ┌────────────┐ │
│  │  API Layer │──>│    Service   │──>│  Backend   │ │
│  │ (FastAPI   │   │    Layer     │   │  Clients   │ │
│  │  routers)  │   │ (business    │   │ (OpenStack │ │
│  │            │   │  logic)      │   │  /K8s/     │ │
│  │            │<──│              │<──│  Ansible)  │ │
│  └────────────┘   └──────────────┘   └────────────┘ │
│        │                                   │         │
│        v                                   v         │
│  ┌──────────┐                    ┌───────────────┐  │
│  │ Job      │                    │ Secret Manager│  │
│  │ Engine   │                    │ (OpenBao/     │  │
│  │ (async   │                    │  Vault)       │  │
│  │  workers)│                    └───────────────┘  │
│  └──────────┘                                       │
│        │                                            │
│        v                                            │
│  ┌──────────────┐                                   │
│  │  Database    │                                   │
│  │ (PostgreSQL) │                                   │
│  └──────────────┘                                   │
└──────────────────────────────────────────────────────┘
```

**Layer responsibilities:**

| Layer | Responsibility | Mapping from current ewccli |
|---|---|---|
| **API Layer** | HTTP request/response, input validation (pydantic), auth enforcement, OpenAPI schema | `commands/*.py` Click decorators → FastAPI routers |
| **Service Layer** | Business logic: VM provisioning pipeline, hub-item deployment orchestration, conflict detection, image/flavor resolution | `commands/commons_infra.py`, `commands/hub/hub_command.py` orchestration |
| **Backend Clients** | Thin SDK wrappers: OpenStack SDK, Kubernetes client, Ansible runner | `backends/openstack/backend_ostack.py`, `backends/kubernetes/backend_k8s.py`, `backends/ansible/backend_ansible.py` |

**Key rules:**
- API layer contains **no business logic** — it delegates to services.
- Service layer contains **no HTTP concerns** — it operates on domain
  objects and returns results.
- Backend clients contain **no orchestration** — they expose atomic
  operations (create_server, delete_server, run_playbook, etc.).
- Services are injected into routers via FastAPI `Depends`, enabling
  testing with mock clients.

### 2.3 Repository Layout

**Decision:** Create a separate **`ewc-backend`** repository.

**Rationale:**
- The backend is a long-running service with its own deployment lifecycle,
  CI/CD, dependencies, and release cadence — fundamentally different from
  the CLI's pip-installable package.
- Separate repos allow independent versioning: the CLI can ship a patch
  without redeploying the backend, and vice versa.
- Clear ownership boundary: backend team owns the service; CLI consumers
  depend only on the published OpenAPI contract.

**Proposed repository structure:**

```
ewc-backend/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Settings (pydantic-settings)
│   ├── deps.py                 # Shared FastAPI dependencies
│   ├── api/                    # API layer (routers)
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── profiles.py
│   │   │   ├── servers.py
│   │   │   ├── hub.py
│   │   │   ├── keypairs.py
│   │   │   ├── dns.py
│   │   │   ├── s3.py
│   │   │   └── jobs.py
│   │   └── deps.py             # Request-scoped dependencies
│   ├── services/               # Service layer (business logic)
│   │   ├── auth_service.py
│   │   ├── server_service.py
│   │   ├── hub_service.py
│   │   ├── keypair_service.py
│   │   ├── dns_service.py
│   │   ├── s3_service.py
│   │   └── job_service.py
│   ├── clients/                # Backend clients (SDK wrappers)
│   │   ├── openstack_client.py
│   │   ├── kubernetes_client.py
│   │   └── ansible_client.py
│   ├── models/                 # Pydantic domain models
│   │   ├── server.py
│   │   ├── hub.py
│   │   ├── dns.py
│   │   ├── s3.py
│   │   ├── keypair.py
│   │   ├── auth.py
│   │   └── job.py
│   ├── jobs/                   # Async job definitions & workers
│   │   ├── engine.py           # Job submission, status, results
│   │   ├── worker.py           # Worker process / task runner
│   │   └── tasks/
│   │       ├── server_create.py
│   │       ├── server_delete.py
│   │       ├── hub_deploy.py
│   │       └── dns_check.py
│   ├── db/                     # Database models & migrations
│   │   ├── base.py
│   │   ├── models.py
│   │   └── migrations/
│   └── core/                   # Cross-cutting concerns
│       ├── security.py         # Auth, token validation
│       ├── credentials.py      # OpenStack cred management
│       ├── errors.py           # Error model, exception handlers
│       └── logging.py
├── tests/
├── Containerfile               # Container image definition
├── docker-compose.yml          # Local dev (API + worker + DB + Redis)
├── pyproject.toml
├── README.md
└── docs/
    └── openapi.yaml            # Generated/exported OpenAPI spec
```

**ewccli changes (thin client):**
- Replace all business logic with HTTP calls to the backend API.
- Retain Click/Rich for the terminal UX layer only.
- Configuration simplified: backend URL + auth token.

### 2.4 Deployment Topology

**Decision:** Containerized service deployed as two logical components:
**API workers** (stateless, horizontally scalable) and **Job workers**
(stateful per-job, vertically scalable).

```
                    ┌─────────────┐
                    │   Ingress   │
                    │  (TLS, WAF) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ API Worker│ │API    │ │ API Worker│
        │     #1    │ │Worker │ │     #3    │
        │ (uvicorn) │ │  #2   │ │ (uvicorn) │
        └─────┬─────┘ └───┬───┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │   Redis     │  (job queue / pub-sub)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │Job Worker │ │Job    │ │Job Worker │
        │     #1    │ │Worker │ │     #3    │
        │(ansible,  │ │  #2   │ │           │
        │ openstack)│ │       │ │           │
        └─────┬─────┘ └───┬───┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼──────┐ ┌───▼──────┐
        │PostgreSQL │ │ OpenBao  │ │  OpenStack│
        │  (jobs,   │ │ (secrets)│ │  / K8s    │
        │  profiles)│ │          │ │           │
        └───────────┘ └──────────┘ └───────────┘
```

**Component details:**

| Component | Technology | Purpose | Scaling |
|---|---|---|---|
| API Workers | FastAPI + Uvicorn (behind gunicorn) | Serve HTTP requests, validate input, enqueue jobs | Horizontal (stateless) |
| Job Workers | Python processes consuming Redis queue | Execute long-running operations (VM create, Ansible, DNS check) | Horizontal with concurrency limits |
| Redis | Valkey/Redis | Job queue (via RQ or ARQ), pub-sub for log streaming | Single/cluster |
| PostgreSQL | PostgreSQL 16 | Job state, profiles, audit log | Primary/replica |
| OpenBao (proposed) | OpenBao (Vault fork) | Secret storage: OpenStack application credentials, SSH keys | HA cluster |

> **Secret-store decision (proposed, not final):** OpenBao is the
> recommended secret store because the team already has experimental
> familiarity with it. It is **not** in production today. Alternatives
> (Kubernetes Secrets + SOPS, cloud managed secret manager, PostgreSQL +
> envelope encryption) are evaluated in the
> [auth model §5.1](./auth-authorization-model.md). The service layer
> talks to a `SecretStore` port so the implementation is swappable.
| Container Runtime | Podman/Docker + Kubernetes | Orchestration of all components | — |

**Container image:** A single `Containerfile` builds an image that can run
as either an API worker or a job worker (entrypoint selected by env var),
reducing build/distribution complexity. Ansible and OpenStack SDK
dependencies are baked into the image.

### 2.5 CLI↔Backend Communication Model

**Decision:** **REST + async job polling/streaming**.

**Communication patterns by operation type:**

| Operation Type | Pattern | Examples |
|---|---|---|
| **Synchronous** (< 5 s) | REST request/response (200) | List servers, show server, list hub items, show hub item, list DNS records, list S3 buckets |
| **Asynchronous** (minutes) | REST submission (202 + job_id) → poll status → fetch result | Create server, delete server, deploy hub item, create DNS record, create S3 bucket, reconfigure server |
| **Streaming** (real-time logs) | Server-Sent Events (SSE) | Deployment logs, Ansible output, DNS resolution progress |

**Synchronous flow:**
```
CLI                          Backend
 │                              │
 │── GET /v1/servers ──────────>│
 │<── 200 OK [{ ... }] ─────────│
 │                              │
```

**Asynchronous flow:**
```
CLI                          Backend
 │                              │
 │── POST /v1/servers ────────>│  (create VM)
 │<── 202 Accepted ────────────│  { "job_id": "abc-123", "status": "pending" }
 │                              │
 │── GET /v1/jobs/abc-123 ────>│  (poll)
 │<── 200 { "status": "running" }│
 │                              │
 │── GET /v1/jobs/abc-123 ────>│  (poll)
 │<── 200 { "status": "completed", "result": {...} }│
 │                              │
```

**Streaming flow (optional, for real-time output):**
```
CLI                          Backend
 │                              │
 │── POST /v1/servers ────────>│  (create VM)
 │<── 202 { "job_id": "abc-123" }│
 │                              │
 │── GET /v1/jobs/abc-123/logs >│  (Accept: text/event-stream)
 │<── data: {"level":"info",...}│
 │<── data: {"level":"info",...}│
 │<── data: {"event":"done"} ──│
 │                              │
```

**Why not WebSocket?** SSE is simpler, works over HTTP/2, is
unidirectional (server→client) which matches the log-streaming use case,
and does not require connection upgrade. The CLI can fall back to polling
if SSE is unavailable.

**Why not gRPC?** REST + JSON is more accessible to AI agents (which
consume OpenAPI/JSON schemas natively) and to curl/HTTP debugging. The
payload sizes are small; binary streaming is not a requirement.

### 2.6 AI Agent-Friendly API Design

**Decision:** The API is designed as a first-class tool surface for AI
agents, with structured schemas, predictable error codes, idempotency,
and discoverable metadata.

**Design principles:**

1. **Resource-oriented REST.** Every entity is a noun under a stable
   versioned prefix (`/v1/`). Agents can infer URL patterns from the
   OpenAPI spec.

2. **Structured JSON everywhere.** No plain-text responses. Every
   response is a JSON object with a consistent envelope:
   ```json
   {
     "data": { ... },
     "meta": { "request_id": "uuid", "pagination": { ... } }
   }
   ```

3. **Machine-readable errors.** All error responses use a standard
   problem-detail format (RFC 9457) with typed error codes:
   ```json
   {
     "type": "https://ewc-backend/docs/errors/credential-expired",
     "title": "OpenStack credential expired",
     "status": 401,
     "detail": "The application credential has expired. Run login to refresh.",
     "instance": "/v1/servers",
     "code": "CREDENTIAL_EXPIRED",
     "retry_after_login": true
   }
   ```

4. **Idempotency keys.** All mutating endpoints accept an
   `Idempotency-Key` header. The backend deduplicates: if the same key is
   seen within 24 h, the original response is replayed. This lets agents
   retry safely without creating duplicate resources.

5. **OpenAPI as the contract.** The spec is published at
   `/openapi.json` (served by FastAPI) and committed to the repository.
   Agents can load it as a tool definition.

6. **Discoverability endpoint.** `GET /v1/capabilities` returns a
   machine-readable catalog of available operations, their parameters,
   and expected durations, so an agent can plan before acting.

7. **Dry-run everywhere.** Every mutating endpoint accepts `?dry_run=true`
   which returns the planned action (the CRD/Kubernetes manifest, the
   Ansible playbook path, the server config) without executing. This lets
   agents validate inputs before committing.

8. **Consistent pagination.** List endpoints use cursor-based pagination
   with `limit`/`cursor` parameters and return `next_cursor` in metadata.

### 2.7 Agent Authorization Model

**Decision:** AI agents authenticate to the backend via **OAuth2 client
credentials** (machine-to-machine) or **scoped API tokens**, with
fine-grained permission scopes.

**Agent auth flow:**
```
Agent                        Keycloak               ewc-backend
  │                              │                       │
  │── POST /token ──────────────>│                       │
  │   (client_id, client_secret, │                       │
  │    grant_type=client_creds)  │                       │
  │<── { access_token, scope } ──│                       │
  │                              │                       │
  │── GET /v1/servers ──────────────────────────────────>│
  │   Authorization: Bearer <token>                      │
  │<── 200 [{ ... }] ────────────────────────────────────│
```

**Scopes (examples):**
| Scope | Permits |
|---|---|
| `servers:read` | List/show servers |
| `servers:write` | Create/delete/reconfigure servers |
| `hub:read` | List/show hub items |
| `hub:deploy` | Deploy hub items |
| `dns:read` | List/describe DNS records |
| `dns:write` | Create/delete DNS records |
| `s3:read` | List S3 buckets |
| `s3:write` | Create/delete S3 buckets |
| `keypairs:read` | List keypairs |
| `keypairs:write` | Create/delete keypairs |
| `jobs:read` | View job status/logs |
| `jobs:cancel` | Cancel running jobs |

**Agent registration:**
1. An administrator registers an agent as an OAuth2 client in Keycloak
   (or creates a scoped API token via the backend admin API).
2. The client is assigned specific scopes based on what the agent is
   authorized to do.
3. The agent obtains an access token via client_credentials grant.
4. Every request includes the Bearer token; the backend validates the
   token and enforces scope-based authorization on each endpoint.

**Human CLI auth:** Human users continue to use the browser-based OIDC
flow (authorization code + PKCE), obtaining a token with their personal
scopes. The CLI caches the token and refreshes it automatically.

---

## 3. Consequences

### Positive
- **Centralized credential management:** OpenStack application credentials
  live in a server-side secret store (proposed: OpenBao), not on user
  laptops. Rotation is a backend operation invisible to CLI users.
- **Resumable operations:** Long-running jobs survive CLI disconnects;
  users can reconnect and check status.
- **Single source of truth:** All business logic in one service, testable
  in isolation, with a versioned OpenAPI contract.
- **Agent-ready:** AI agents can discover, plan, and execute operations
  via structured HTTP + OpenAPI, without terminal scraping.
- **Multi-consumer:** Future web UIs, CI pipelines, and orchestration
  tools all consume the same API.

### Negative
- **Infrastructure overhead:** The backend requires PostgreSQL, Redis,
  OpenBao, and container orchestration — more moving parts than a CLI.
- **Network dependency:** The CLI now requires network access to the
  backend; offline operation is no longer possible.
- **Latency:** An extra HTTP hop for every operation (mitigated by the
  backend being co-located with OpenStack/K8s in the same network).
- **Migration effort:** ewccli must be rewritten as a thin client;
  existing profiles need migration.

### Mitigations
- The backend is containerized and can run on a single node initially;
  components can be split out as scale demands.
- The CLI can cache read responses (server lists, hub items) for
  short-term offline use.
- A migration tool will convert existing `~/.ewccli/profiles` entries to
  backend-managed profiles.

---

## 4. Alternatives Considered

### 4.1 Keep all logic in the CLI
Rejected — does not solve credential exposure, resumability, or
multi-consumer access. The CLI would remain the only integration point.

### 4.2 CLI + shared library (no service)
Package the business logic as a Python library that both the CLI and
other tools import. Rejected — does not solve credential management,
job persistence, or agent access. Library consumers must still manage
their own OpenStack/K8s connections and credential lifecycle.

### 4.3 Serverless functions (Lambda/Functions)
Rejected — Ansible playbooks and OpenStack operations can run for many
minutes; serverless function timeouts (typically 15 min) are too tight
for some operations (DNS check timeout is 20 min). Cold starts add
latency to interactive operations. Debugging is harder.

### 4.4 GraphQL instead of REST
Rejected — REST + OpenAPI is the lingua franca for AI agent tool-use.
GraphQL adds a query language complexity that does not benefit the
resource-oriented, CRUD-like operations of this domain. The OpenAPI
spec doubles as the agent tool definition.

---

## 5. Open Questions (for future phases)

1. **Multi-tenancy isolation:** Should each federee (ECMWF, EUMETSAT)
   have a separate backend instance, or should one backend serve both
   with tenant isolation? (Phase 2 decision.)
2. **Job persistence retention:** How long to keep completed job records
   and logs? (Default proposal: 30 days, configurable.)
3. **Webhook callbacks:** Should the backend support webhook callbacks
   for job completion (in addition to polling/SSE)? (Phase 2 — useful
   for CI integrations.)
4. **Rate limiting:** Per-agent rate limits to prevent runaway automation?
   (Phase 2.)

---

## 6. References

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [OpenAPI 3.1 specification](https://spec.openapis.org/oas/v3.1.0)
- [RFC 9457 — Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc9457)
- [OAuth 2.0 Client Credentials Grant](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4)
- ewccli source: `EWCCLI_INFRA_FUNCTIONALITY.md` (capability inventory)
- OpenAPI spec: [`openapi.yaml`](./openapi.yaml)
- Auth model: [`auth-authorization-model.md`](./auth-authorization-model.md)
- Job model: [`job-execution-model.md`](./job-execution-model.md)
