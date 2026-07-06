"""Profiles API router — CLI profile management."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import idempotency_key
from app.models.common import DataEnvelope, ProblemDetail
from app.models.profile import Profile, ProfileCreate, ProfileUpdate
from app.services.exceptions import ConfigServiceError

router = APIRouter(prefix="/profiles", tags=["Profiles"])

# In-memory profile store for Phase 4
_profiles: dict[str, Profile] = {}


@router.get("", response_model=DataEnvelope[list[Profile]])
async def list_profiles() -> DataEnvelope[list[Profile]]:
    """List all profiles."""
    return DataEnvelope(data=list(_profiles.values()))


@router.post("", response_model=DataEnvelope[Profile], status_code=201)
async def create_profile(
    req: ProfileCreate,
    idempotency_key: Optional[str] = Depends(idempotency_key),
) -> DataEnvelope[Profile]:
    """Create a new profile."""
    profile_id = f"{req.federee.lower()}-{req.region.lower()}-{req.tenant_name.lower()}"
    if profile_id in _profiles:
        raise HTTPException(
            status_code=409,
            detail=ProblemDetail(
                type="about:blank",
                title="Profile already exists",
                status=409,
                detail=f"Profile '{profile_id}' already exists.",
                code="PROFILE_EXISTS",
            ).model_dump(),
        )
    now = datetime.now(timezone.utc)
    profile = Profile(
        profile_id=profile_id,
        federee=req.federee,
        region=req.region,
        tenant_name=req.tenant_name,
        ssh_public_key_path=req.ssh_public_key_path,
        ssh_private_key_path=req.ssh_private_key_path,
        created_at=now,
        updated_at=now,
    )
    _profiles[profile_id] = profile
    return DataEnvelope(data=profile)


@router.get("/{profileId}", response_model=DataEnvelope[Profile])
async def show_profile(profileId: str) -> DataEnvelope[Profile]:
    """Show a profile by ID."""
    profile = _profiles.get(profileId)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank",
                title="Not Found",
                status=404,
                detail=f"Profile '{profileId}' not found.",
                code="NOT_FOUND",
            ).model_dump(),
        )
    return DataEnvelope(data=profile)


@router.put("/{profileId}", response_model=DataEnvelope[Profile])
async def update_profile(
    profileId: str,
    req: ProfileUpdate,
) -> DataEnvelope[Profile]:
    """Update a profile."""
    profile = _profiles.get(profileId)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank",
                title="Not Found",
                status=404,
                detail=f"Profile '{profileId}' not found.",
                code="NOT_FOUND",
            ).model_dump(),
        )
    if req.ssh_public_key_path is not None:
        profile.ssh_public_key_path = req.ssh_public_key_path
    if req.ssh_private_key_path is not None:
        profile.ssh_private_key_path = req.ssh_private_key_path
    profile.updated_at = datetime.now(timezone.utc)
    return DataEnvelope(data=profile)


@router.delete("/{profileId}", status_code=204)
async def delete_profile(profileId: str) -> None:
    """Delete a profile."""
    if profileId not in _profiles:
        raise HTTPException(
            status_code=404,
            detail=ProblemDetail(
                type="about:blank",
                title="Not Found",
                status=404,
                detail=f"Profile '{profileId}' not found.",
                code="NOT_FOUND",
            ).model_dump(),
        )
    del _profiles[profileId]
