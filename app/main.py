"""FastAPI application factory for ewc-backend."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.config import Settings, get_settings
from app.logging import RequestIdMiddleware, configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("lifespan")
    logger.info("ewc_backend_starting", debug=settings.debug)
    yield
    logger.info("ewc_backend_stopping")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title="EWC Backend API",
        version="1.0.0",
        description=(
            "REST API for the European Weather Cloud (EWC) backend service. "
            "This API extracts all business logic from ewccli into a standalone "
            "backend. The CLI and AI agents interact with infrastructure "
            "(OpenStack, Kubernetes, Ansible) exclusively through these endpoints."
        ),
        license_info={"name": "GPL-3.0-or-later", "url": "https://www.gnu.org/licenses/gpl-3.0.html"},
        contact={"name": "EWC Support", "email": "support@europeanweather.cloud"},
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    from app.models.common import ProblemDetail
    from app.services.exceptions import ServiceError

    @app.exception_handler(ServiceError)
    async def service_error_handler(request, exc: ServiceError):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content=ProblemDetail(
                type="about:blank",
                title="Service Error",
                status=400,
                detail=str(exc),
                code="SERVICE_ERROR",
            ).model_dump(),
        )

    # Health/readiness endpoints (outside /v1 prefix)
    @app.get("/healthz", tags=["Health"])
    async def healthz() -> dict:
        """Liveness probe — returns 200 if the process is alive."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["Health"])
    async def readyz() -> dict:
        """Readiness probe — returns 200 if the service is ready to serve."""
        return {"status": "ready"}

    # API v1 routes
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    return app


# Module-level app instance for uvicorn: `uvicorn app.main:app`
app = create_app()
