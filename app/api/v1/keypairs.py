"""Keypairs API router — OpenStack SSH keypairs."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import dry_run_param, get_keypair_service, idempotency_key
from app.api.deps import get_job_service
from app.jobs.engine import JobEngine
from app.models.common import DataEnvelope, ListEnvelope, JobRefEnvelope
from app.models.keypair import Keypair, KeypairCreate
from app.services.keypair_service import KeypairService

router = APIRouter(prefix="/keypairs", tags=["Keypairs"])


@router.get("", response_model=ListEnvelope[Keypair])
async def list_keypairs(
    service: KeypairService = Depends(get_keypair_service),
) -> ListEnvelope[Keypair]:
    """List OpenStack keypairs."""
    keypairs = service.list_keypairs()
    return ListEnvelope(data=keypairs)


@router.post("", response_model=JobRefEnvelope, status_code=202)
async def create_keypair(
    req: KeypairCreate,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: KeypairService = Depends(get_keypair_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Create a keypair (async)."""
    def _executor():
        return service.create_keypair(req, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="keypair",
        resource_name=req.keypair_name,
        operation="create",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)


@router.delete("/{keypairName}", response_model=JobRefEnvelope, status_code=202)
async def delete_keypair(
    keypairName: str,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: KeypairService = Depends(get_keypair_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Delete a keypair (async)."""
    def _executor():
        return service.delete_keypair(keypairName, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="keypair",
        resource_name=keypairName,
        operation="delete",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)
