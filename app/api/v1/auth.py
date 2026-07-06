"""Auth API router — login, callback, token, logout."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from app.api.deps import get_auth_service
from app.models.auth import LoginInitResponse, TokenRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/login", response_model=LoginInitResponse)
async def initiate_login(
    no_browser: bool = Query(default=False),
    profile: Optional[str] = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginInitResponse:
    """Initiate OIDC login — returns the Keycloak authorization URL."""
    return auth_service.initiate_login(no_browser=no_browser, profile=profile)


@router.get("/callback")
async def auth_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """OIDC callback — receives the authorization code from Keycloak."""
    # In production, exchange code for tokens and redirect to CLI
    return RedirectResponse(url=f"ewc://callback?code={code}&state={state}", status_code=302)


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    req: TokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Exchange an authorization code or refresh token for tokens."""
    return auth_service.exchange_token(
        grant_type=req.grant_type,
        code=req.code,
        refresh_token=req.refresh_token,
        client_id=req.client_id,
        client_secret=req.client_secret,
        redirect_uri=req.redirect_uri,
    )


@router.post("/logout", status_code=204)
async def logout(
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Logout / revoke the current token."""
    auth_service.logout()
