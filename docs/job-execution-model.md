# Long-Running Job Execution Model

| Field | Value |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-07-03 |
| **Related ADR** | ADR-001 |
| **Related Issue** | KAM-6 |

---

## 1. Overview

Many ewccli operations are long-running:

| Operation | Typical Duration | Current Timeout |
|---|---|---|
| VM creation (OpenStack) | 2–10 min | None (blocking) |
| Hub-item deployment (VM + Ansible) | 5–20 min | None (blocking) |
| DNS record resolution check | up to 20 min | 20 min (`DNS_CHECK_TIMEOUT_MINUTES`) |
| VM deletion | 1–5 min | None (blocking) |
| DNS record creation (K8s CRD) | < 30 s | None (blocking) |
| S3 bucket creation (K8s CRD) | < 30 s | None (blocking) |

The current CLI blocks the terminal for the entire duration. If the CLI
is killed, the operation is lost with no way to check status or retrieve
results. The backend solves this with an **asynchronous job model**.

---

## 2. Job Lifecycle

### 2.1 States

```
                 ┌─────────┐
                 │ PENDING │
                 └────┬────┘
                      │ worker picks up
                      v
                 ┌─────────┐
         ┌──────│ RUNNING │──────┐
         │      └────┬────┘      │
         │           │           │
    cancel      complete/fail   timeout
         │           │           │
         v           v           v
  ┌──────────┐ ┌──────────┐ ┌─────────┐
  │CANCELLED │ │COMPLETED │ │ FAILED  │
  └──────────┘ └──────────┘ └─────────┘
         │           │           │
         └─────┬─────┘──────────┘
               v
          ┌─────────┐
          │ TERMINAL│  (retained for query; no state transitions)
          └─────────┘
```

| State | Description |
|---|---|
| `pending` | Job accepted, queued, not yet started by a worker |
| `running` | Worker is executing the job |
| `completed` | Job finished successfully; result available |
| `failed` | Job finished with an error; error details available |
| `cancelled` | Job was cancelled by user/admin before or during execution |
| `timeout` | Job exceeded its timeout limit (subtype of `failed`) |

### 2.2 Job Submission

Long-running operations are submitted via `POST` and return `202 Accepted`
with a job reference:

**Request:**
```
POST /v1/servers
Content-Type: application/json
Idempotency-Key: <uuid>

{
  "server_name": "my-vm",
  "image_name": "Rocky-9",
  "flavour_name": "4cpu-4gbmem",
  "networks": ["private"],
  "security_groups": ["ssh"],
  "keypair_name": "my-keypair",
  "external_ip": false,
  "dry_run": false,
  "force": false
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "job_01HZX...",
    "status": "pending",
    "resource_type": "server",
    "resource_name": "my-vm",
    "operation": "create",
    "created_at": "2026-07-03T12:00:00Z",
    "estimated_duration_seconds": 600
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

### 2.3 Job Status Query

**Request:**
```
GET /v1/jobs/job_01HZX...
```

**Response (200):**
```json
{
  "data": {
    "job_id": "job_01HZX...",
    "status": "running",
    "resource_type": "server",
    "resource_name": "my-vm",
    "operation": "create",
    "created_at": "2026-07-03T12:00:00Z",
    "started_at": "2026-07-03T12:00:05Z",
    "progress": 45,
    "progress_message": "Waiting for server to become active...",
    "estimated_remaining_seconds": 330,
    "timeout_at": "2026-07-03T12:20:05Z"
  },
  "meta": {
    "request_id": "req_def456"
  }
}
```

**Completed response (200):**
```json
{
  "data": {
    "job_id": "job_01HZX...",
    "status": "completed",
    "resource_type": "server",
    "resource_name": "my-vm",
    "operation": "create",
    "created_at": "2026-07-03T12:00:00Z",
    "started_at": "2026-07-03T12:00:05Z",
    "completed_at": "2026-07-03T12:08:30Z",
    "progress": 100,
    "result": {
      "server_name": "my-vm",
      "status": "ACTIVE",
      "internal_ip": "10.0.0.42",
      "external_ip": null,
      "flavor": "4cpu-4gbmem",
      "image": "Rocky-9.6-20260620",
      "keypair": "my-keypair"
    }
  }
}
```

**Failed response (200):**
```json
{
  "data": {
    "job_id": "job_01HZX...",
    "status": "failed",
    "resource_type": "server",
    "resource_name": "my-vm",
    "operation": "create",
    "created_at": "2026-07-03T12:00:00Z",
    "started_at": "2026-07-03T12:00:05Z",
    "completed_at": "2026-07-03T12:03:15Z",
    "error": {
      "code": "SERVER_CREATE_FAILED",
      "message": "OpenStack returned error: quota exceeded for instances",
      "retryable": false,
      "details": { "quota_limit": 10, "quota_used": 10 }
    }
  }
}
```

### 2.4 Job Logs

Logs are available via polling or SSE streaming.

**Polling:**
```
GET /v1/jobs/job_01HZX.../logs?cursor=<cursor>&limit=100
```

**Response (200):**
```json
{
  "data": {
    "logs": [
      {
        "timestamp": "2026-07-03T12:00:05Z",
        "level": "info",
        "message": "Creating OpenStack connection..."
      },
      {
        "timestamp": "2026-07-03T12:00:07Z",
        "level": "info",
        "message": "Resolving image Rocky-9 → Rocky-9.6-20260620"
      },
      {
        "timestamp": "2026-07-03T12:00:10Z",
        "level": "info",
        "message": "Creating keypair my-keypair..."
      }
    ],
    "has_more": true,
    "next_cursor": "log_cursor_xyz"
  }
}
```

**SSE streaming:**
```
GET /v1/jobs/job_01HZX.../logs
Accept: text/event-stream

data: {"timestamp":"...","level":"info","message":"Creating OpenStack connection..."}

data: {"timestamp":"...","level":"info","message":"Resolving image Rocky-9 → Rocky-9.6-20260620"}

data: {"timestamp":"...","level":"info","message":"Server created, waiting for ACTIVE state..."}

data: {"event":"job_completed","status":"completed","job_id":"job_01HZX..."}
```

### 2.5 Job Outputs

For jobs that produce artifacts (e.g., hub-item deployment outputs,
kubeconfigs), outputs are retrievable after completion:

```
GET /v1/jobs/job_01HZX.../outputs
```

**Response (200):**
```json
{
  "data": {
    "outputs": [
      {
        "name": "ssh_command",
        "type": "text",
        "value": "ssh -i ~/.ewccli/.ssh/default_id_rsa cloud-user@10.0.0.42"
      },
      {
        "name": "ansible_log",
        "type": "log",
        "value": "PLAY [provision] ****************************\n..."
      }
    ]
  }
}
```

### 2.6 Job Cancellation

```
POST /v1/jobs/job_01HZX.../cancel
```

**Response (200):**
```json
{
  "data": {
    "job_id": "job_01HZX...",
    "status": "cancelled",
    "cancelled_at": "2026-07-03T12:05:00Z"
  }
}
```

Cancellation semantics:
- If the job is `pending`: removed from queue, marked `cancelled`.
- If the job is `running`: a cancellation signal is sent to the worker.
  The worker attempts graceful cleanup (e.g., delete the partially-created
  VM). The job is marked `cancelled` after cleanup.
- If the job is terminal: returns `409 Conflict` (cannot cancel a
  completed/failed job).

### 2.7 Job Listing

```
GET /v1/jobs?status=running&resource_type=server&limit=20&cursor=<cursor>
```

**Response (200):**
```json
{
  "data": [
    { "job_id": "job_...", "status": "running", "resource_type": "server", ... },
    { "job_id": "job_...", "status": "pending", "resource_type": "hub", ... }
  ],
  "meta": {
    "pagination": {
      "limit": 20,
      "next_cursor": "job_cursor_abc"
    }
  }
}
```

---

## 3. Timeout Configuration

Each job type has a configurable timeout. If a job exceeds its timeout,
the worker aborts and marks the job as `failed` with error code
`JOB_TIMEOUT`.

| Job Type | Default Timeout | Configurable Via |
|---|---|---|
| Server create | 30 min | `JOB_TIMEOUT_SERVER_CREATE` env var |
| Server delete | 15 min | `JOB_TIMEOUT_SERVER_DELETE` env var |
| Hub deploy | 30 min | `JOB_TIMEOUT_HUB_DEPLOY` env var |
| DNS record create | 5 min | `JOB_TIMEOUT_DNS_CREATE` env var |
| DNS resolution check | 20 min | `JOB_TIMEOUT_DNS_CHECK` env var (preserves current `DNS_CHECK_TIMEOUT_MINUTES`) |
| S3 bucket create | 5 min | `JOB_TIMEOUT_S3_CREATE` env var |
| Keypair create | 2 min | `JOB_TIMEOUT_KEYPAIR_CREATE` env var |

The `timeout_at` field in the job status response lets clients know the
deadline.

---

## 4. Job Engine Architecture

### 4.1 Components

```
API Worker                Redis (Queue)           Job Worker
     │                         │                       │
     │── enqueue(job) ────────>│                       │
     │                         │── dequeue(job) ──────>│
     │                         │                       │── execute
     │                         │                       │
     │                   ┌─────┴─────┐                 │
     │                   │  Pub/Sub  │<── log/progress─│
     │<── subscribe ─────│  channel  │                 │
     │                   └───────────┘                 │
     │                                                  │
     │             PostgreSQL                           │
     │── write status ─────────────────────────────────>│
     │<── read status ──────────────────────────────────│
```

**Queue:** Redis-backed job queue (using [RQ](https://python-rq.org/) or
[ARQ](https://arq-docs.helpmanual.io/)). Jobs are enqueued by API
workers and dequeued by job workers.

**Status persistence:** Job state (status, progress, result, error) is
persisted in PostgreSQL. This survives worker restarts and allows status
queries from any API worker.

**Log streaming:** Workers publish log/progress events to a Redis
pub/sub channel. API workers subscribe to the channel when an SSE client
connects, bridging pub/sub to SSE. Logs are also persisted to PostgreSQL
for later retrieval via polling.

### 4.2 Worker Concurrency

- Each job worker processes one job at a time (Ansible and OpenStack
  operations are CPU/network-bound, not I/O-async).
- Multiple worker processes run per container (configurable via
  `JOB_WORKER_CONCURRENCY`).
- Worker pods scale horizontally based on queue depth (HPA on
  `rq_queue_length` metric).

### 4.3 Retry & Error Handling

- **Transient failures** (OpenStack 503, network timeout): retried
  automatically up to 3 times with exponential backoff.
- **Permanent failures** (quota exceeded, invalid image): no retry; job
  marked `failed` with error details.
- **Partial failures** (VM created but Ansible failed): the job is
  marked `failed` with error details, and any cleanup actions (e.g.,
  delete the partial VM if `auto_cleanup_on_failure=true`) are noted in
  the job outputs.

### 4.4 Idempotency

When an `Idempotency-Key` header is provided:
1. The backend checks if a job with that key already exists.
2. If found and still active: returns the existing job (HTTP 200 with
   current status).
3. If found and terminal: returns the original result (HTTP 200 with
   final status and result).
4. If not found: creates a new job (HTTP 202).

This allows clients and agents to retry safely after network failures
without creating duplicate resources.

---

## 5. Mapping: CLI Operations → Job Types

| CLI Command | API Endpoint | Job Type | Sync/Async |
|---|---|---|---|
| `ewc login` | `POST /v1/auth/login` | — (sync, OIDC redirect) | Sync |
| `ewc infra create` | `POST /v1/servers` | `server_create` | Async |
| `ewc infra list` | `GET /v1/servers` | — | Sync |
| `ewc infra show` | `GET /v1/servers/{name}` | — | Sync |
| `ewc infra delete` | `DELETE /v1/servers/{name}` | `server_delete` | Async |
| `ewc infra create --force` (reconfigure) | `POST /v1/servers` with `force=true` | `server_reconfigure` | Async |
| `ewc hub list` | `GET /v1/hub/items` | — | Sync |
| `ewc hub show` | `GET /v1/hub/items/{name}` | — | Sync |
| `ewc hub deploy` | `POST /v1/hub/items/{name}/deploy` | `hub_deploy` | Async |
| `ewc dns create` | `POST /v1/dns/records` | `dns_create` | Async |
| `ewc dns get` | `GET /v1/dns/records` | — | Sync |
| `ewc dns describe` | `GET /v1/dns/records/{name}` | — | Sync |
| `ewc dns delete` | `DELETE /v1/dns/records/{name}` | `dns_delete` | Async |
| `ewc s3 bucket create` | `POST /v1/s3/buckets` | `s3_create` | Async |
| `ewc s3 bucket get` | `GET /v1/s3/buckets` | — | Sync |
| `ewc s3 bucket delete` | `DELETE /v1/s3/buckets/{name}` | `s3_delete` | Async |

---

## 6. CLI Integration

The thin-client CLI handles the async flow transparently:

1. **Submit:** `ewc infra create my-vm` → `POST /v1/servers` → receives
   `job_id`.
2. **Poll:** CLI polls `GET /v1/jobs/{job_id}` every 5 seconds.
3. **Display:** CLI shows a progress bar / spinner with `progress_message`.
4. **Stream (optional):** If `--follow` flag is passed, CLI opens an SSE
   connection to `/v1/jobs/{job_id}/logs` and streams logs in real-time.
5. **Result:** On completion, CLI displays the result (server details, SSH
   command, etc.).
6. **Resume:** If the CLI is interrupted, `ewc jobs show <job_id>` or
   `ewc jobs list` shows the job status. The user can `ewc jobs follow
   <job_id>` to resume streaming.
