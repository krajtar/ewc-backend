"""Common Pydantic models shared across endpoints."""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ProblemDetail(BaseModel):
    """RFC 9457 problem detail with EWC-specific extensions."""

    type: str = "about:blank"
    title: Optional[str] = None
    status: Optional[int] = None
    detail: Optional[str] = None
    instance: Optional[str] = None
    code: Optional[str] = Field(
        default=None, description="Machine-readable error code (e.g., CREDENTIAL_EXPIRED)."
    )
    retryable: Optional[bool] = Field(
        default=None, description="Whether the client should retry the request."
    )
    required_scopes: Optional[list[str]] = Field(
        default=None, description="Required OAuth2 scopes (for 403 errors)."
    )


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    request_id: Optional[str] = None
    pagination: Optional["PaginationInfo"] = None


class PaginationInfo(BaseModel):
    limit: int = 50
    next_cursor: Optional[str] = None


class DataEnvelope(BaseModel, Generic[T]):
    """Standard envelope wrapping a single resource in ``data``."""

    data: T


class ListEnvelope(BaseModel, Generic[T]):
    """Standard envelope wrapping a list of resources in ``data``."""

    data: list[T]
    meta: Optional[PaginationMeta] = None


class JobRefEnvelope(BaseModel):
    """Envelope for async job acceptance responses."""

    data: "JobRef"  # noqa: F821 - forward ref resolved at runtime


# Forward-reference resolution
from app.models.job import JobRef  # noqa: E402

JobRefEnvelope.model_rebuild()
