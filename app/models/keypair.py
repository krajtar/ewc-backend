"""Keypair-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel


class Keypair(BaseModel):
    name: str
    fingerprint: Optional[str] = None
    public_key: Optional[str] = None


class KeypairCreate(BaseModel):
    keypair_name: str
    public_key: Optional[str] = None
    ssh_public_key_path: Optional[str] = None
