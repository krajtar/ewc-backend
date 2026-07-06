"""S3 bucket-related Pydantic models."""

from typing import Any, Optional

from pydantic import BaseModel


class S3Bucket(BaseModel):
    name: str
    namespace: Optional[str] = None
    owner: Optional[str] = None
    write_access_ids: list[str] = []
    read_access_ids: list[str] = []
    geo_enabled: bool = False
    created_at: Optional[str] = None
    status: Optional[dict[str, Any]] = None


class S3BucketCreate(BaseModel):
    bucket_name: str
    access_id: str
    write_access_ids: list[str] = []
    write_access_refs_ids: list[str] = []
    read_access_ids: list[str] = []
    read_access_refs_ids: list[str] = []
    geo_enabled: bool = False
