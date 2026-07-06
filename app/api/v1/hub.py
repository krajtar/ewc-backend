"""Hub API router — EWC Community Hub items."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import dry_run_param, get_hub_service, idempotency_key, pagination
from app.api.deps import get_job_service
from app.jobs.engine import JobEngine
from app.models.common import DataEnvelope, ListEnvelope, PaginationMeta, JobRefEnvelope
from app.models.hub import HubDeployRequest, HubItemDetail, HubItemSummary
from app.services.hub_service import HubService

router = APIRouter(prefix="/hub/items", tags=["Hub"])


@router.get("", response_model=ListEnvelope[HubItemSummary])
async def list_hub_items(
    force_refresh: bool = Query(default=False),
    pagination: dict = Depends(pagination),
    service: HubService = Depends(get_hub_service),
) -> ListEnvelope[HubItemSummary]:
    """List all hub items."""
    items = service.list_items(force_refresh=force_refresh)
    limit = pagination["limit"]
    page = items[:limit]
    next_cursor = items[limit].name if len(items) > limit else None
    meta = PaginationMeta(pagination={"limit": limit, "next_cursor": next_cursor})
    return ListEnvelope(data=page, meta=meta)


@router.get("/{itemName}", response_model=DataEnvelope[HubItemDetail])
async def show_hub_item(
    itemName: str,
    service: HubService = Depends(get_hub_service),
) -> DataEnvelope[HubItemDetail]:
    """Show hub item details."""
    detail = service.show_item(itemName)
    if not detail:
        raise HTTPException(status_code=404, detail={"type": "about:blank", "title": "Not Found", "status": 404, "detail": f"Hub item '{itemName}' not found.", "code": "NOT_FOUND"})
    return DataEnvelope(data=detail)


@router.post("/{itemName}/deploy", response_model=JobRefEnvelope, status_code=202)
async def deploy_hub_item(
    itemName: str,
    req: HubDeployRequest,
    dry_run: bool = Depends(dry_run_param),
    idempotency_key: Optional[str] = Depends(idempotency_key),
    service: HubService = Depends(get_hub_service),
    job_engine: JobEngine = Depends(get_job_service),
) -> JobRefEnvelope:
    """Deploy a hub item (async)."""
    req.item_name = itemName

    def _executor():
        return service.deploy_item(itemName, req.server_name, req.inputs, req.profile)

    job_ref = await job_engine.submit(
        resource_type="hub",
        resource_name=itemName,
        operation="deploy",
        executor=_executor,
        idempotency_key=idempotency_key,
        dry_run=dry_run,
    )
    return JobRefEnvelope(data=job_ref)
