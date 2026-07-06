"""Auth-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel


class LoginInitData(BaseModel):
    authorization_url: str
    state: str
    profile: Optional[str] = None


class LoginInitResponse(BaseModel):
    data: LoginInitData


class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 900
    scope: Optional[str] = None
