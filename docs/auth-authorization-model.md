# Authentication & Authorization Model

| Field | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-07-03 |
| **Related ADR** | ADR-001 |
| **Related Issue** | KAM-6 |

---

## 1. Overview

This document defines how authentication and authorization work in the
`ewc-backend` architecture. It covers three distinct trust boundaries:

1. **User/CLI → Backend** — how human users and the CLI authenticate to
   the backend service.
2. **Agent → Backend** — how AI agents authenticate and are authorized
   with scoped permissions.
3. **Backend → OpenStack/K8s** — how the backend holds, rotates, and uses
   OpenStack application credentials and Kubernetes tokens.

---

## 2. Current State (ewccli)

> **At a glance:** Today the CLI holds **long-term** OpenStack application
credentials in **files on the user's local disk**
(`~/.ewccli/profiles`, plaintext INI). The user provides application
credentials directly to `ewc login`; the CLI persists them and calls
OpenStack/Kubernetes itself. There is no identity provider, no OIDC,
and no backend. An OpenBao JWT login was explored as an experiment but
is **not** the production flow.

### 2.1 What actually runs in production

1. **Credential provision by the user** — the user obtains OpenStack
   application credentials (`application_credential_id` +
   `application_credential_secret`) manually from the EWC web portal and
   provides them to `ewc login` via CLI arguments, environment variables
   (`OS_APPLICATION_CREDENTIAL_ID` / `OS_APPLICATION_CREDENTIAL_SECRET`),
   interactive prompts, or an existing `~/.config/openstack/clouds.yaml`.
   There is no identity provider, no OIDC, no browser redirect, and no
   token ceremony — the credentials are entered directly.
2. **Local persistence** — `ewc login` writes the application credential
   ID/secret, federee, region, tenant name, and SSH key paths to
   `~/.ewccli/profiles` on disk in **plaintext** (INI format via
   `configparser`).
3. **Direct cloud access** — on every subsequent command (`ewc server
   list`, `ewc hub deploy`, …) the CLI **reads the long-term credentials
   from the local files** and authenticates **directly** to OpenStack
   (Keystone) and Kubernetes. No backend is involved.

### 2.2 OpenBao JWT — experiment only (not in production)

An **OpenBao JWT login** path (exchanging a JWT for an OpenBao client
token and reading credentials from KV2) was explored as an experiment.
It is **not** part of the production CLI, **not** deployed as the
standard flow, and **not** how any user authenticates today. It is
relevant to this design only as prior art for the *target* secret-store
decision (§5); it must not be read as the current production behaviour.

### 2.3 Problems with the current state

- **Long-term credentials on disk in plaintext** — the primary exposure
  risk; credentials persist between sessions and survive logout.
- **Rotation forces every user to re-run `ewc login`** — there is no
  server-side rotation.
- **No per-user revocation** — revoking one user means rotating for
  everyone (or no one).
- **No client-side expiry tracking** — the CLI discovers expiry only when
  OpenStack returns 401/403 mid-operation.
- **No shared state** — every CLI invocation re-reads files and re-drives
  the cloud SDKs itself; there is no central authority.

---

## 3. Target Model: User/CLI → Backend

### 3.1 Authentication

The CLI authenticates to the backend using **OAuth 2.0 Authorization Code
flow with PKCE** (a new pattern — the current CLI has no identity-provider
integration; this introduces Keycloak as the OIDC IdP and the backend as
the resource server).

```
User (browser)         CLI                  Keycloak            ewc-backend
     │                   │                      │                     │
     │── login ─────────>│                      │                     │
     │                   │── auth URL + PKCE ──>│                     │
     │<── browser auth ──│                      │                     │
     │                   │<── auth code ────────│                     │
     │                   │── token exchange ───>│                     │
     │                   │<── access_token ─────│                     │
     │                   │                      │                     │
     │                   │── GET /v1/servers ───────────────────────>│
     │                   │   Authorization: Bearer <access_token>     │
     │                   │<── 200 [{ ... }] ──────────────────────────│
```

**Token lifecycle:**
- Access tokens are short-lived (15 min default, configurable).
- Refresh tokens are long-lived (8 h default) and stored by the CLI in
  the OS keychain (not plaintext on disk).
- The CLI automatically refreshes tokens before they expire.
- `--no-browser` mode prints the auth URL for headless/SSH environments
  (same as current behavior).

### 3.2 Backend as OAuth2 Resource Server

The backend validates incoming JWTs using Keycloak's public keys (JWKS).
No database lookup is needed for token validation — the JWT is
self-contained.

**Validation checks:**
- Signature (JWKS from Keycloak).
- `exp` (expiry).
- `iss` (issuer = Keycloak URL).
- `aud` (audience = `ewc-backend`).
- Scope claims (see §3.3).

### 3.3 Authorization (Scopes)

User permissions are encoded as OAuth2 scopes in the JWT. The backend
enforces scope-based authorization on every endpoint.

| Scope | Endpoints | Description |
|---|---|---|
| `profile:read` | `GET /v1/profiles` | View own profiles |
| `profile:write` | `POST /v1/profiles`, `PUT /v1/profiles/{id}` | Create/update profiles |
| `servers:read` | `GET /v1/servers`, `GET /v1/servers/{name}` | List/show servers |
| `servers:write` | `POST /v1/servers`, `DELETE /v1/servers/{name}` | Create/delete/reconfigure servers |
| `hub:read` | `GET /v1/hub/items`, `GET /v1/hub/items/{name}` | List/show hub items |
| `hub:deploy` | `POST /v1/hub/items/{name}/deploy` | Deploy hub items |
| `keypairs:read` | `GET /v1/keypairs` | List keypairs |
| `keypairs:write` | `POST /v1/keypairs`, `DELETE /v1/keypairs/{name}` | Create/delete keypairs |
| `dns:read` | `GET /v1/dns/records` | List DNS records |
| `dns:write` | `POST /v1/dns/records`, `DELETE /v1/dns/records/{name}` | Create/delete DNS records |
| `s3:read` | `GET /v1/s3/buckets` | List S3 buckets |
| `s3:write` | `POST /v1/s3/buckets`, `DELETE /v1/s3/buckets/{name}` | Create/delete S3 buckets |
| `jobs:read` | `GET /v1/jobs`, `GET /v1/jobs/{id}`, `GET /v1/jobs/{id}/logs` | View job status/logs |
| `jobs:cancel` | `POST /v1/jobs/{id}/cancel` | Cancel running jobs |

Default user scope set: all `*:read` + `*:write` scopes (full access for
human users via the CLI).

---

## 4. Target Model: Agent → Backend

### 4.1 Authentication

AI agents authenticate via **OAuth 2.0 Client Credentials grant**
(machine-to-machine, no user interaction).

```
Agent                Keycloak               ewc-backend
  │                      │                       │
  │── POST /token ──────>│                       │
  │   client_id          │                       │
  │   client_secret      │                       │
  │   grant_type=        │                       │
  │     client_credentials│                      │
  │<── access_token ─────│                       │
  │   (scopes)           │                       │
  │                      │                       │
  │── GET /v1/servers ──────────────────────────>│
  │   Authorization: Bearer <token>              │
  │<── 200 [{ ... }] ────────────────────────────│
```

**Agent registration:**
1. An administrator creates an OAuth2 client in Keycloak for the agent.
2. The client is assigned specific scopes (e.g., `servers:read
   hub:deploy jobs:read`).
3. The agent stores its `client_id` and `client_secret` securely
   (environment variable, secret manager, or config file with 0600
   permissions).
4. The agent obtains an access token via the client_credentials grant
   and refreshes it as needed (tokens are short-lived).

### 4.2 Alternative: Scoped API Tokens

For simpler integrations (e.g., CI pipelines without Keycloak access),
the backend supports **long-lived API tokens** created via the admin API:

```
POST /v1/admin/tokens
  {
    "name": "ci-deploy-agent",
    "scopes": ["servers:write", "hub:deploy", "jobs:read"],
    "expires_at": "2026-12-31T23:59:59Z"
  }

→ 201 Created
  {
    "token": "ewc_<opaque>",
    "token_id": "tok_abc123",
    "name": "ci-deploy-agent",
    "scopes": [...],
    "expires_at": "..."
  }
```

These tokens are:
- Opaque (not JWTs) — validated via database lookup.
- Revocable at any time via `DELETE /v1/admin/tokens/{token_id}`.
- Scoped (same scope model as OAuth2).
- Stored hashed in the database (only shown once at creation time).

**Usage:**
```
GET /v1/servers
  Authorization: Bearer ewc_<opaque>
```

### 4.3 Agent Authorization Enforcement

Every API endpoint declares its required scope(s). The backend's
dependency injection checks the token's scopes against the required
scope before the handler runs.

```python
# Example (FastAPI)
@router.post("/v1/servers", status_code=202)
@require_scope("servers:write")
async def create_server(...):
    ...
```

If the token lacks the required scope:
```json
{
  "type": "https://ewc-backend/docs/errors/insufficient-scope",
  "title": "Insufficient scope",
  "status": 403,
  "detail": "Token lacks required scope: servers:write",
  "code": "INSUFFICIENT_SCOPE",
  "required_scopes": ["servers:write"],
  "token_scopes": ["servers:read"]
}
```

---

## 5. Backend → OpenStack Credential Management

> **Scope note:** This section describes the **target** design. It is a
> *proposal*, not the current state (the current state is long-term
> credentials in local files — see §2). OpenBao is **not** in production
> use today; the OpenBao JWT login in the current CLI is only an
> experiment (§2.2). The secret-store choice below is a decision to be
> ratified in Phase 2.

### 5.1 Credential Storage (proposed)

**Proposed decision:** store OpenStack application credentials in
**OpenBao** (Vault-compatible) KV2, not in the database or on client disk.
OpenBao is chosen because the team already has experimental familiarity
with it (§2.2) and it provides versioning, audit logging, and dynamic
secrets out of the box.

**Alternatives considered for the secret store:**

| Option | Pros | Cons |
|---|---|---|
| **OpenBao / HashiCorp Vault** (proposed) | KV versioning, audit log, dynamic secrets, lease revocation; team has prior experiment | Extra HA component to operate; another trust boundary |
| **Kubernetes Secrets + Sealed Secrets / SOPS** | No new component if already on K8s; GitOps-friendly | No dynamic secrets; rotation logic must be hand-built; weaker audit |
| **Cloud managed secret manager** (e.g. Barbican) | Fully managed; native to OpenStack deployments | Vendor lock-in; latency from control plane; harder self-host |
| **PostgreSQL + envelope encryption (KMS)** | Fewest new components; transactions with job state | Must build key rotation, audit, and access policy from scratch |

The interface is deliberately abstracted behind a `SecretStore` port so
the implementation can be swapped without touching the service layer.

**Secret path convention:**

**Secret path convention:**
```
ewc-backend/data/openstack-credentials/{federee}/{region}/{tenant_id}
```

**Secret payload:**
```json
{
  "application_credential_id": "...",
  "application_credential_secret": "...",
  "auth_url": "https://keystone...",
  "federee": "EUMETSAT",
  "region": "ECIS-R1",
  "tenant_name": "...",
  "created_at": "2026-07-01T10:00:00Z",
  "expires_at": null,
  "last_rotated_at": "2026-07-01T10:00:00Z",
  "rotation_count": 0
}
```

### 5.2 Credential Retrieval (per-request)

When the backend needs to call OpenStack on behalf of a user:

1. The request is authenticated (user or agent token).
2. The backend resolves the user's tenant/profile to determine which
   OpenStack credential to use.
3. The backend authenticates to OpenBao using its own service token
   (not the user's token).
4. The backend reads the credential from OpenBao KV2.
5. The backend creates an OpenStack connection using the credential.
6. The connection is used for the duration of the request (or job) and
   then discarded.

**Credential caching:** OpenStack connections are cached per-tenant for
a short TTL (5 min) to avoid repeated OpenBao reads for rapid successive
requests. The cache is invalidated on credential rotation.

### 5.3 Credential Rotation

**Automated rotation:**

The backend runs a scheduled rotation task (daily) that:

1. Lists all OpenStack credentials in OpenBao.
2. For each credential older than the rotation threshold (default: 30 days):
   a. Authenticates to OpenStack with the current credential.
   b. Creates a new application credential via the OpenStack Identity API
      (`POST /v3/auth/tokens` → `POST /v3/application_credentials`).
   c. Stores the new credential in OpenBao (new version via KV2).
   d. Deletes the old application credential from OpenStack.
   e. Updates `last_rotated_at` and increments `rotation_count`.
3. In-flight jobs that hold the old credential are allowed to complete
   (grace period); new requests use the new credential.

**Manual rotation (admin API):**
```
POST /v1/admin/credentials/rotate
  {
    "federee": "EUMETSAT",
    "region": "ECIS-R1",
    "tenant_id": "..."
  }
```

**Expiry detection:** If OpenStack returns 401/403 for a credential, the
backend:
1. Marks the credential as `expired` in OpenBao.
2. Returns a `CREDENTIAL_EXPIRED` error (HTTP 401) to the caller.
3. Triggers an immediate rotation attempt.
4. If rotation fails, alerts the operations team.

### 5.4 Kubernetes Credential Management

Kubernetes access uses kubeconfigs obtained during the login flow (via
KKP API → OIDC kubeconfig). The backend:

1. Stores kubeconfigs in OpenBao at
   `ewc-backend/data/kubeconfigs/{tenant_id}`.
2. Uses the kubeconfig to create a Kubernetes client per tenant.
3. Kubeconfig tokens are refreshed by the backend's kubelogin exec
   plugin (same mechanism as the current CLI, but server-side).

---

## 6. Security Considerations

| Concern | Mitigation |
|---|---|
| Token theft (CLI) | Refresh tokens in OS keychain; short-lived access tokens |
| Token theft (agent) | Client secrets in secret manager; short-lived access tokens; revocable API tokens |
| OpenStack credential exposure | Stored in OpenBao, never sent to client; connections created server-side only |
| OpenBao compromise | OpenBao HA cluster with mTLS; audit logging; least-privilege policy for backend service token |
| Privilege escalation | Scopes enforced per-endpoint; admin operations require `admin` scope |
| Replay attacks | `Idempotency-Key` deduplication; nonces for sensitive operations |
| SSRF | Backend egress restricted to known OpenStack/K8s/OpenBao endpoints via network policy |

---

## 7. Migration Path

1. **Phase 1 (this ticket):** Define the model (this document) + OpenAPI
   spec. No code changes.
2. **Phase 2:** Implement the backend auth endpoints, Keycloak resource
   server configuration, and OpenBao integration.
3. **Phase 3:** Update `ewc login` to obtain a backend token (instead of
   storing OpenStack credentials locally). Provide a migration tool that
   moves existing profiles to backend-managed storage.
4. **Phase 4:** Remove local credential storage from the CLI entirely;
   the CLI only holds the backend auth token.
