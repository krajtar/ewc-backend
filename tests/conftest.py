"""Shared test fixtures for ewc-backend API tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a TestClient for the FastAPI app."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory stores before each test for isolation."""
    from app.api import deps
    from app.api.v1 import profiles as profiles_module
    from app.jobs import engine as engine_module

    # Reset profiles store
    profiles_module._profiles.clear()

    # Reset OpenStack stub backend
    deps._openstack_backend._servers.clear()
    deps._openstack_backend._keypairs.clear()

    # Reset Kubernetes stub backend
    deps._k8s_backend._crds.clear()

    # Reset job engine singleton
    if engine_module._job_engine is not None:
        engine_module._job_engine._jobs.clear()
        engine_module._job_engine._logs.clear()
        engine_module._job_engine._outputs.clear()

    yield
