"""Servers API router — OpenStack VM lifecycle."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import dry_run_param, get_server_service, idempotency_key, pagination
from app.jobs.engine import JobEngine, get_job_service
from app.models.common import DataEnvelope, ListEnvelope, PaginationMeta, JobRefEnvelope
from app.models.server import ServerCreate, ServerConflict, ServerDetail, ServerSummary
from app.models.job import JobRef
from app.services.server_service import ServerService

router = APIRouter(prefix="/servers", tags=["Servers"])


@router.get("", response_model=ListEnvelope[ServerSummary])
async def list_servers(
    show_all: bool = Query(default=False),
    pagination: dict = Depends(pagination),
    service: ServerService = Depends(get_server_service),
) -> ListEnvelope[ServerSummary]:
    """List OpenStack servers."""
    servers = service.list_servers(show_all=show_all)
    # Simple pagination
    limit = pagination["limit"]
    cursor = pagination["cursor"]
    start = 0
    if cursor:
        for i, s in enumerate(servers):
            if s.name == cursor:
                start = i + 1
                break
    page = servers[start : start + limit]
    next_cursor = page[-1].name if start + limit < len(servers) and page else None
    meta = PaginationMeta(pagination={"limit": limit, "next_cursor": next_cursor})
    return ListEnvelope(data=page, meta=meta)


@router.post("", response_model=JobRefEnvelope, status_code=202)
async def create_server(
    req: ServerCreate,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: ServerService = Depends(get_server_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Create a server (async). Returns 202 with a job reference."""
    # Check for conflicts if not force
    if not req.force:
        existing = service.show_server(req.server_name)
        if existing:
            conflict = service.check_conflict(req.server_name, req.model_dump(), existing.model_dump())
            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail=conflict.model_dump(),
                )

    def _executor():
        return service.create_server(req.model_dump(), dry_run=dry_run, force=req.force)

    job_ref = await job_engine.submit(
        resource_type="server",
        resource_name=req.server_name,
        operation="create",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)


@router.get("/{serverName}", response_model=DataEnvelope[ServerDetail])
async def show_server(
    serverName: str,
    service: ServerService = Depends(get_server_service),
) -> DataEnvelope[ServerDetail]:
    """Show server details."""
    detail = service.show_server(serverName)
    if not detail:
        raise HTTPException(status_code=404, detail={"type": "about:blank", "title": "Not Found", "status": 404, "detail": f"Server '{serverName}' not found.", "code": "NOT_FOUND"})
    return DataEnvelope(data=detail)


@router.delete("/{serverName}", response_model=JobRefEnvelope, status_code=202)
async def delete_server(
    serverName: str,
    force: bool = Query(default=False),
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: ServerService = Depends(get_server_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Delete a server (async)."""
    def _executor():
        return service.delete_server(serverName, force=force, dry_run=dry_run)

    job_ref = await job_engine.submit(
        resource_type="server",
        resource_name=serverName,
        operation="delete",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)


@router.post("/{serverName}/reconfigure", response_model=JobRefEnvelope, status_code=202)
async def reconfigure_server(
    serverName: str,
    req: ServerCreate,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: ServerService = Depends(get_server_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Reconfigure an existing server (async)."""
    req.server_name = serverName
    req.force = True

    def _executor():
        return service.create_server(req.model_dump(), dry_run=dry_run, force=True)

    job_ref = await job_engine.submit(
        resource_type="server",
        resource_name=serverName,
        operation="reconfigure",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)
