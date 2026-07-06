"""Profile-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Profile(BaseModel):
    profile_id: str
    federee: str
    region: str
    tenant_name: str
    ssh_public_key_path: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    kubeconfig_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileCreate(BaseModel):
    federee: str
    region: str
    tenant_name: str
    ssh_public_key_path: Optional[str] = None
    ssh_private_key_path: Optional[str] = None


class ProfileUpdate(BaseModel):
    ssh_public_key_path: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    refresh_credentials: bool = False
