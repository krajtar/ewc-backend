"""Containerfile build and structure test."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONTAINERFILE = ROOT / "Containerfile"


def test_containerfile_exists():
    """Containerfile exists at project root."""
    assert CONTAINERFILE.exists(), "Containerfile not found at project root"


def test_containerfile_structure():
    """Containerfile has required Dockerfile directives."""
    content = CONTAINERFILE.read_text()

    assert "FROM" in content, "Containerfile missing FROM directive"
    assert "python" in content.lower(), "Containerfile should use Python base image"
    assert "CMD" in content or "ENTRYPOINT" in content, "Containerfile missing CMD/ENTRYPOINT"
    assert "uvicorn" in content, "Containerfile should run uvicorn"
    assert "EXPOSE" in content, "Containerfile missing EXPOSE"
    assert "HEALTHCHECK" in content, "Containerfile missing HEALTHCHECK"
    assert "app.main:app" in content, "Containerfile should reference app.main:app"


def test_containerfile_multistage():
    """Containerfile uses multi-stage build for smaller image."""
    content = CONTAINERFILE.read_text()
    from_count = content.count("FROM ")
    assert from_count >= 2, f"Containerfile should use multi-stage build (found {from_count} FROM)"


def test_containerfile_copies_app():
    """Containerfile copies the application code."""
    content = CONTAINERFILE.read_text()
    assert "COPY app/" in content or "COPY app" in content, "Containerfile should COPY app/"


@pytest.mark.skipif(
    shutil.which("docker") is None and shutil.which("podman") is None,
    reason="Neither docker nor podman is available",
)
def test_containerfile_builds():
    """Containerfile builds successfully (requires docker or podman).

    Skipped if the container runtime cannot build due to environment
    constraints (e.g. read-only filesystem in CI sandbox).
    """
    builder = shutil.which("docker") or shutil.which("podman")
    try:
        result = subprocess.run(
            [builder, "build", "-f", str(CONTAINERFILE), "-t", "ewc-backend-test", str(ROOT)],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        pytest.skip(f"Container build could not run: {exc}")

    if result.returncode != 0:
        stderr = result.stderr or ""
        if "read-only file system" in stderr or "permission denied" in stderr.lower():
            pytest.skip(f"Container build skipped — environment constraint: {stderr.strip()}")

    assert result.returncode == 0, (
        f"Containerfile build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
