"""Shared FastAPI dependencies for the API layer."""

from typing import Optional

from fastapi import Depends, Header, Query

from app.clients.stubs import (
    StubAnsibleBackend,
    StubKubernetesBackend,
    StubOpenstackBackend,
)
from app.config import Settings, get_settings
from app.jobs.engine import JobEngine, get_job_engine
from app.services.auth_service import AuthService
from app.services.dns_service import DnsService
from app.services.hub_service import HubService
from app.services.keypair_service import KeypairService
from app.services.s3_service import S3Service
from app.services.server_service import ServerService

# Singleton backend clients
_openstack_backend = StubOpenstackBackend()
_k8s_backend = StubKubernetesBackend()
_ansible_backend = StubAnsibleBackend()


def get_openstack_backend() -> StubOpenstackBackend:
    return _openstack_backend


def get_k8s_backend() -> StubKubernetesBackend:
    return _k8s_backend


def get_ansible_backend() -> StubAnsibleBackend:
    return _ansible_backend


def get_auth_service() -> AuthService:
    return AuthService(get_settings())


def get_server_service() -> ServerService:
    return ServerService(_openstack_backend)


def get_hub_service() -> HubService:
    return HubService(get_settings())


def get_keypair_service() -> KeypairService:
    return KeypairService(_openstack_backend)


def get_dns_service() -> DnsService:
    return DnsService(_k8s_backend)


def get_s3_service() -> S3Service:
    return S3Service(_k8s_backend)


def get_job_service() -> JobEngine:
    return get_job_engine()


def idempotency_key(
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Optional[str]:
    """Extract the Idempotency-Key header."""
    return idempotency_key


def dry_run_param(
    dry_run: bool = Query(default=False, alias="dry_run"),
) -> bool:
    """Extract the dry_run query parameter."""
    return dry_run


def pagination(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: Optional[str] = Query(default=None),
) -> dict:
    """Extract pagination parameters."""
    return {"limit": limit, "cursor": cursor}
