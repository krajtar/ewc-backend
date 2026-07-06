# ewc-backend

Standalone FastAPI backend service for the European Weather Cloud (EWC).

## Overview

`ewc-backend` extracts all business logic from `ewccli` into a standalone
backend service. The CLI and AI agents interact with infrastructure
(OpenStack, Kubernetes, Ansible) exclusively through these REST endpoints.

## Architecture

Three-layer architecture (see [ADR-001](docs/ADR-001-target-architecture.md)):

```
API Layer (FastAPI routers) → Service Layer (business logic) → Backend Clients (SDK wrappers)
```

- **API Layer** (`app/api/`): HTTP request/response, input validation, OpenAPI schema.
- **Service Layer** (`app/services/`): Business logic — VM provisioning, hub deployment, DNS/S3 management.
- **Backend Clients** (`app/clients/`): Protocol interfaces + stub implementations for OpenStack, Kubernetes, Ansible.

## Project Structure

```
ewc-backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Settings (pydantic-settings)
│   ├── logging.py           # Structured logging (structlog) + request tracing
│   ├── api/
│   │   ├── deps.py          # Shared FastAPI dependencies
│   │   └── v1/              # API v1 routers
│   │       ├── auth.py
│   │       ├── profiles.py
│   │       ├── servers.py
│   │       ├── hub.py
│   │       ├── keypairs.py
│   │       ├── dns.py
│   │       ├── s3.py
│   │       ├── jobs.py
│   │       └── capabilities.py
│   ├── services/            # Service layer (business logic)
│   ├── clients/             # Backend client interfaces + stubs
│   ├── models/              # Pydantic domain models
│   └── jobs/                # Async job engine
├── docs/                    # Architecture docs + OpenAPI spec
├── tests/                   # Test suite
├── Containerfile            # Container image build
└── pyproject.toml           # Project configuration
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

### Install & Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.

- Interactive docs: `http://localhost:8000/docs`
- OpenAPI spec: `http://localhost:8000/openapi.json`
- Health: `http://localhost:8000/healthz`

### Run Tests

```bash
uv run pytest
```

### Container Build & Run

```bash
podman build -t ewc-backend .
podman run -p 8000:8000 ewc-backend
```

## Configuration

All settings are loaded from environment variables (prefix `EWC_BACKEND_`):

| Variable | Default | Description |
|---|---|---|
| `EWC_BACKEND_DEBUG` | `false` | Enable debug mode |
| `EWC_BACKEND_LOG_LEVEL` | `INFO` | Log level |
| `EWC_BACKEND_KEYCLOAK_URL` | `https://keycloak.example.com` | Keycloak IdP URL |
| `EWC_BACKEND_KEYCLOAK_REALM` | `ewc` | Keycloak realm |
| `EWC_BACKEND_DATABASE_URL` | — | PostgreSQL connection URL |
| `EWC_BACKEND_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

## API Endpoints

See the [OpenAPI spec](docs/openapi.yaml) for the full contract. Key endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe |
| GET | `/readyz` | Readiness probe |
| GET | `/v1/capabilities` | API capabilities for agent discovery |
| GET | `/v1/auth/login` | Initiate OIDC login |
| POST | `/v1/auth/token` | Exchange code/refresh token |
| GET/POST | `/v1/profiles` | List/create profiles |
| GET/POST/DELETE | `/v1/servers` | OpenStack VM lifecycle |
| GET/POST | `/v1/hub/items` | Hub item list/deploy |
| GET/POST/DELETE | `/v1/keypairs` | SSH keypair management |
| GET/POST/DELETE | `/v1/dns/records` | DNS record management |
| GET/POST/DELETE | `/v1/s3/buckets` | S3 bucket management |
| GET | `/v1/jobs` | Job status, logs, outputs |

## License

GPL-3.0-or-later
