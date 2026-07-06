"""Server-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServerNetwork(BaseModel):
    network: str
    addresses: list[str] = []


class ServerSummary(BaseModel):
    name: str
    status: Optional[str] = None
    networks: Optional[str] = None
    flavor: Optional[str] = None
    id: Optional[str] = None


class ServerDetail(BaseModel):
    name: str
    id: Optional[str] = None
    status: Optional[str] = None
    flavor: Optional[str] = None
    image: Optional[str] = None
    networks: list[ServerNetwork] = []
    security_groups: list[str] = []
    keypair: Optional[str] = None
    internal_ip: Optional[str] = None
    external_ip: Optional[str] = None
    created_at: Optional[datetime] = None


class ServerCreate(BaseModel):
    server_name: str = Field(..., max_length=63)
    image_name: str = "Rocky-9"
    flavour_name: Optional[str] = None
    networks: list[str] = []
    security_groups: list[str] = []
    keypair_name: Optional[str] = None
    external_ip: bool = False
    force: bool = False
    ssh_public_key_path: Optional[str] = None
    ssh_private_key_path: Optional[str] = None


class ServerConflictDiff(BaseModel):
    field: str
    current: Optional[str] = None
    requested: Optional[str] = None


class ServerConflict(BaseModel):
    code: str = "SERVER_CONFIG_CONFLICT"
    server_name: str
    diffs: list[ServerConflictDiff] = []
    message: str = "Use force=true to reconfigure."
