"""Job-related Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    timeout = "timeout"


class JobError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Optional[dict[str, Any]] = None


class JobRef(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    resource_type: str
    resource_name: str
    operation: str
    created_at: datetime
    estimated_duration_seconds: int = 600


class Job(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    resource_type: str
    resource_name: str
    operation: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    progress_message: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None
    timeout_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[JobError] = None
    idempotency_key: Optional[str] = None


class LogEntry(BaseModel):
    timestamp: datetime
    level: str = "info"
    message: str
    source: Optional[str] = None


class JobOutput(BaseModel):
    name: str
    type: str = "text"
    value: str


class CapabilitiesOperation(BaseModel):
    method: str
    path: str
    summary: Optional[str] = None
    async_: bool = False
    required_scopes: list[str] = []
    estimated_duration_seconds: Optional[int] = None
    supports_dry_run: bool = False


class CapabilitiesData(BaseModel):
    version: str = "1.0.0"
    operations: list[CapabilitiesOperation] = []


class CapabilitiesResponse(BaseModel):
    data: CapabilitiesData
