"""In-memory async job engine.

Manages job lifecycle: pending -> running -> completed/failed/cancelled.
Phase 5 (KAM-10) will replace this with a Redis-backed persistent engine.
"""

import asyncio
import inspect
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from app.logging import get_logger
from app.models.job import Job, JobError, JobRef, JobStatus, LogEntry

_logger = get_logger(__name__)

# Estimated durations by operation type (seconds)
_ESTIMATED_DURATIONS: dict[str, int] = {
    "create": 600,
    "delete": 300,
    "deploy": 900,
    "reconfigure": 600,
    "dns_check": 1200,
}


class JobEngine:
    """In-memory job store and async execution manager."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._logs: dict[str, list[LogEntry]] = {}
        self._outputs: dict[str, list[Any]] = {}
        self._idempotency: dict[str, str] = {}  # key -> job_id
        self._lock = asyncio.Lock()

    async def submit(
        self,
        resource_type: str,
        resource_name: str,
        operation: str,
        executor: Optional[Callable] = None,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False,
    ) -> JobRef:
        """Submit a new job. Returns a JobRef immediately."""
        # Idempotency check
        if idempotency_key and idempotency_key in self._idempotency:
            existing_id = self._idempotency[idempotency_key]
            existing = self._jobs.get(existing_id)
            if existing:
                return self._to_ref(existing)

        job_id = f"job_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        est = _ESTIMATED_DURATIONS.get(operation, 600)

        job = Job(
            job_id=job_id,
            status=JobStatus.pending,
            resource_type=resource_type,
            resource_name=resource_name,
            operation=operation,
            created_at=now,
            timeout_at=now + timedelta(seconds=est * 2),
            idempotency_key=idempotency_key,
        )

        if dry_run:
            job.status = JobStatus.completed
            job.progress = 100
            job.completed_at = now
            job.result = {"dry_run": True, "resource_type": resource_type, "resource_name": resource_name}
            self._add_log(job_id, "info", f"Dry run: would {operation} {resource_type} '{resource_name}'", "job_engine")
        else:
            if idempotency_key:
                self._idempotency[idempotency_key] = job_id

        async with self._lock:
            self._jobs[job_id] = job
            self._logs[job_id] = []
            self._outputs[job_id] = []

        if not dry_run:
            # Schedule async execution
            asyncio.create_task(self._execute(job_id, executor))

        return self._to_ref(job)

    async def _execute(self, job_id: str, executor: Optional[Callable]) -> None:
        """Execute a job asynchronously."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        self._add_log(job_id, "info", f"Starting {job.operation} for {job.resource_type} '{job.resource_name}'", "job_engine")

        try:
            if executor:
                result = await executor() if inspect.iscoroutinefunction(executor) else executor()
                job.result = result
                if isinstance(result, dict) and "outputs" in result:
                    self._outputs[job_id] = result["outputs"]
            job.status = JobStatus.completed
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            self._add_log(job_id, "info", f"Job completed: {job.operation} for '{job.resource_name}'", "job_engine")
        except Exception as exc:
            job.status = JobStatus.failed
            job.error = JobError(
                code=f"{job.resource_type.upper()}_{job.operation.upper()}_FAILED",
                message=str(exc),
                retryable=False,
            )
            job.completed_at = datetime.now(timezone.utc)
            self._add_log(job_id, "error", f"Job failed: {exc}", "job_engine")
            _logger.error("job_failed", job_id=job_id, error=str(exc))

    def _add_log(self, job_id: str, level: str, message: str, source: str) -> None:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            source=source,
        )
        if job_id not in self._logs:
            self._logs[job_id] = []
        self._logs[job_id].append(entry)

    def _to_ref(self, job: Job) -> JobRef:
        return JobRef(
            job_id=job.job_id,
            status=job.status,
            resource_type=job.resource_type,
            resource_name=job.resource_name,
            operation=job.operation,
            created_at=job.created_at,
            estimated_duration_seconds=_ESTIMATED_DURATIONS.get(job.operation, 600),
        )

    async def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def list_jobs(
        self,
        status_filter: Optional[str] = None,
        resource_type_filter: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> tuple[list[Job], Optional[str]]:
        """List jobs with optional filters. Returns (jobs, next_cursor)."""
        jobs = list(self._jobs.values())

        if status_filter:
            jobs = [j for j in jobs if j.status.value == status_filter]
        if resource_type_filter:
            jobs = [j for j in jobs if j.resource_type == resource_type_filter]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Simple cursor pagination
        start = 0
        if cursor:
            for i, j in enumerate(jobs):
                if j.job_id == cursor:
                    start = i + 1
                    break

        page = jobs[start : start + limit]
        next_cursor = None
        if start + limit < len(jobs):
            next_cursor = page[-1].job_id if page else None

        return page, next_cursor

    async def get_logs(
        self,
        job_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> tuple[list[LogEntry], bool, Optional[str]]:
        """Get paginated log entries for a job."""
        logs = self._logs.get(job_id, [])

        start = 0
        if cursor:
            for i, entry in enumerate(logs):
                if entry.timestamp.isoformat() == cursor:
                    start = i + 1
                    break

        page = logs[start : start + limit]
        has_more = start + limit < len(logs)
        next_cursor = page[-1].timestamp.isoformat() if has_more and page else None

        return page, has_more, next_cursor

    async def get_outputs(self, job_id: str) -> Optional[list[Any]]:
        return self._outputs.get(job_id)

    async def cancel(self, job_id: str) -> Optional[Job]:
        """Cancel a job. Returns the updated job or None if not found."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        if job.status in (JobStatus.completed, JobStatus.failed, JobStatus.cancelled, JobStatus.timeout):
            return job  # Already terminal

        job.status = JobStatus.cancelled
        job.completed_at = datetime.now(timezone.utc)
        self._add_log(job_id, "info", "Job cancelled by user", "job_engine")
        return job


# Singleton instance
_job_engine: Optional[JobEngine] = None


def get_job_engine() -> JobEngine:
    """Return the singleton job engine instance."""
    global _job_engine
    if _job_engine is None:
        _job_engine = JobEngine()
    return _job_engine


# Alias for backward compatibility with router imports
get_job_service = get_job_engine
