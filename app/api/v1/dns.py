"""DNS API router — DNS record management via Kubernetes CRD."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import dry_run_param, get_dns_service, idempotency_key, pagination
from app.jobs.engine import JobEngine, get_job_service
from app.models.common import DataEnvelope, ListEnvelope, PaginationMeta, JobRefEnvelope
from app.models.dns import DnsRecord, DnsRecordCreate
from app.services.dns_service import DnsService

router = APIRouter(prefix="/dns/records", tags=["DNS"])


@router.get("", response_model=ListEnvelope[DnsRecord])
async def list_dns_records(
    pagination: dict = Depends(pagination),
    service: DnsService = Depends(get_dns_service),
) -> ListEnvelope[DnsRecord]:
    """List DNS records."""
    records = service.list_records()
    limit = pagination["limit"]
    page = records[:limit]
    next_cursor = page[-1].name if len(records) > limit and page else None
    meta = PaginationMeta(pagination={"limit": limit, "next_cursor": next_cursor})
    return ListEnvelope(data=page, meta=meta)


@router.post("", response_model=JobRefEnvelope, status_code=202)
async def create_dns_record(
    req: DnsRecordCreate,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: DnsService = Depends(get_dns_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Create a DNS record (async)."""
    def _executor():
        return service.create_record(req, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="dns",
        resource_name=req.record_name,
        operation="create",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)


@router.get("/{recordName}", response_model=DataEnvelope[DnsRecord])
async def show_dns_record(
    recordName: str,
    service: DnsService = Depends(get_dns_service),
) -> DataEnvelope[DnsRecord]:
    """Show a DNS record."""
    record = service.show_record(recordName)
    if not record:
        raise HTTPException(status_code=404, detail={"type": "about:blank", "title": "Not Found", "status": 404, "detail": f"DNS record '{recordName}' not found.", "code": "NOT_FOUND"})
    return DataEnvelope(data=record)


@router.delete("/{recordName}", response_model=JobRefEnvelope, status_code=202)
async def delete_dns_record(
    recordName: str,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: DnsService = Depends(get_dns_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Delete a DNS record (async)."""
    def _executor():
        return service.delete_record(recordName, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="dns",
        resource_name=recordName,
        operation="delete",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)
