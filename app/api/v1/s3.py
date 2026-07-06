"""S3 API router — S3 bucket management via Kubernetes CRD."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import dry_run_param, get_s3_service, idempotency_key, pagination
from app.api.deps import get_job_service
from app.jobs.engine import JobEngine
from app.models.common import DataEnvelope, ListEnvelope, PaginationMeta, JobRefEnvelope
from app.models.s3 import S3Bucket, S3BucketCreate
from app.services.s3_service import S3Service

router = APIRouter(prefix="/s3/buckets", tags=["S3"])


@router.get("", response_model=ListEnvelope[S3Bucket])
async def list_s3_buckets(
    pagination: dict = Depends(pagination),
    service: S3Service = Depends(get_s3_service),
) -> ListEnvelope[S3Bucket]:
    """List S3 buckets."""
    buckets = service.list_buckets()
    limit = pagination["limit"]
    page = buckets[:limit]
    next_cursor = page[-1].name if len(buckets) > limit and page else None
    meta = PaginationMeta(pagination={"limit": limit, "next_cursor": next_cursor})
    return ListEnvelope(data=page, meta=meta)


@router.post("", response_model=JobRefEnvelope, status_code=202)
async def create_s3_bucket(
    req: S3BucketCreate,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: S3Service = Depends(get_s3_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Create an S3 bucket (async)."""
    def _executor():
        return service.create_bucket(req, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="s3",
        resource_name=req.bucket_name,
        operation="create",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)


@router.delete("/{bucketName}", response_model=JobRefEnvelope, status_code=202)
async def delete_s3_bucket(
    bucketName: str,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: S3Service = Depends(get_s3_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Delete an S3 bucket (async)."""
    def _executor():
        return service.delete_bucket(bucketName, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="s3",
        resource_name=bucketName,
        operation="delete",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)
