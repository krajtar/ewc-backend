"""Jobs API router — job status, logs, outputs, cancellation."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_job_service, pagination
from app.jobs.engine import JobEngine
from app.models.common import DataEnvelope, ListEnvelope, PaginationMeta, ProblemDetail
from app.models.job import Job, LogEntry, JobOutput

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=ListEnvelope[Job])
async def list_jobs(
    status: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    pagination: dict = Depends(pagination),
    job_engine: JobEngine = Depends(get_job_service),
) -> ListEnvelope[Job]:
    """List jobs for the authenticated user/tenant."""
    jobs, next_cursor = await job_engine.list_jobs(
        status_filter=status,
        resource_type_filter=resource_type,
        limit=pagination["limit"],
        cursor=pagination["cursor"],
    )
    meta = PaginationMeta(pagination={"limit": pagination["limit"], "next_cursor": next_cursor})
    return ListEnvelope(data=jobs, meta=meta)


@router.get("/{jobId}", response_model=DataEnvelope[Job])
async def get_job(
    jobId: str,
    job_engine: JobEngine = Depends(get_job_service),
) -> DataEnvelope[Job]:
    """Get job status."""
    job = await job_engine.get_job(jobId)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank", title="Not Found", status=404,
                detail=f"Job '{jobId}' not found.", code="NOT_FOUND",
            ).model_dump(),
        )
    return DataEnvelope(data=job)


@router.get("/{jobId}/logs")
async def get_job_logs(
    jobId: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    follow: bool = Query(default=False),
    job_engine: JobEngine = Depends(get_job_service),
) -> dict:
    """Get job logs (polling mode)."""
    job = await job_engine.get_job(jobId)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank", title="Not Found", status=404,
                detail=f"Job '{jobId}' not found.", code="NOT_FOUND",
            ).model_dump(),
        )
    logs, has_more, next_cursor = await job_engine.get_logs(jobId, limit=limit, cursor=cursor)
    return {
        "data": {
            "logs": [log.model_dump(mode="json") for log in logs],
            "has_more": has_more,
            "next_cursor": next_cursor,
        }
    }


@router.get("/{jobId}/outputs", response_model=DataEnvelope[dict])
async def get_job_outputs(
    jobId: str,
    job_engine: JobEngine = Depends(get_job_service),
) -> DataEnvelope[dict]:
    """Get job outputs/artifacts."""
    job = await job_engine.get_job(jobId)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank", title="Not Found", status=404,
                detail=f"Job '{jobId}' not found.", code="NOT_FOUND",
            ).model_dump(),
        )
    outputs = await job_engine.get_outputs(jobId) or []
    return DataEnvelope(data={"outputs": [o if isinstance(o, dict) else o.model_dump() for o in outputs]})


@router.post("/{jobId}/cancel", response_model=DataEnvelope[Job])
async def cancel_job(
    jobId: str,
    job_engine: JobEngine = Depends(get_job_service),
) -> DataEnvelope[Job]:
    """Cancel a running job."""
    job = await job_engine.cancel(jobId)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank", title="Not Found", status=404,
                detail=f"Job '{jobId}' not found.", code="NOT_FOUND",
            ).model_dump(),
        )
    if job.status in ("completed", "failed", "cancelled", "timeout"):
        raise HTTPException(
            status_code=409,
            detail=ProblemDetail(
                type="about:blank", title="Conflict", status=409,
                detail=f"Job '{jobId}' is already in a terminal state.",
                code="JOB_TERMINAL",
            ).model_dump(),
        )
    return DataEnvelope(data=job)
