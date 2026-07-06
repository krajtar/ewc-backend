"""DNS-related Pydantic models."""

from typing import Any, Optional

from pydantic import BaseModel


class DnsRecord(BaseModel):
    name: str
    type: str
    rdata: str
    namespace: Optional[str] = None
    owner: Optional[str] = None
    write_access_ids: list[str] = []
    read_access_ids: list[str] = []
    geo_enabled: bool = False
    created_at: Optional[str] = None
    status: Optional[dict[str, Any]] = None


class DnsRecordCreate(BaseModel):
    record_name: str
    record_type: str
    rdata: str
    access_id: Optional[str] = None
    write_access_ids: list[str] = []
    write_access_refs_ids: list[str] = []
    read_access_ids: list[str] = []
    read_access_refs_ids: list[str] = []
    geo_enabled: bool = False
