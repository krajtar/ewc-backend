"""Hub-related Pydantic models."""

from typing import Any, Optional

from pydantic import BaseModel


class HubItemAnnotations(BaseModel):
    technology: list[str] = []
    category: list[str] = []
    other: list[str] = []


class HubItemSummary(BaseModel):
    name: str
    title: Optional[str] = None
    version: Optional[str] = None
    summary: Optional[str] = None
    annotations: Optional[HubItemAnnotations] = None


class HubItemInput(BaseModel):
    name: str
    mandatory: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None


class HubItemSource(BaseModel):
    type: str
    url: Optional[str] = None
    ref: Optional[str] = None


class HubItemEwccli(BaseModel):
    inputs: list[HubItemInput] = []
    default_image_name: Optional[str] = None
    default_security_groups: list[str] = []
    path_to_main_file: Optional[str] = None
    path_to_requirements_file: Optional[str] = None
    external_ip: bool = False
    check_dns: bool = False


class HubItemDetail(BaseModel):
    name: str
    title: Optional[str] = None
    version: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    sources: list[HubItemSource] = []
    ewccli: Optional[HubItemEwccli] = None


class HubDeployRequest(BaseModel):
    item_name: str
    server_name: str
    inputs: dict[str, Any] = {}
    profile: Optional[str] = None
