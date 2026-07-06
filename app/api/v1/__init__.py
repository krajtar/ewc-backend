"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, capabilities, dns, hub, jobs, keypairs, profiles, s3, servers

router = APIRouter()
router.include_router(capabilities.router)
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(servers.router)
router.include_router(hub.router)
router.include_router(keypairs.router)
router.include_router(dns.router)
router.include_router(s3.router)
router.include_router(jobs.router)
