# ewc-backend Containerfile
# Builds a single image that runs the FastAPI API worker via uvicorn.

FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml README.md ./
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY app/ app/
COPY docs/ docs/

# Install the project itself
RUN uv sync --no-dev

# ─── Runtime stage ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the virtual environment and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/docs /app/docs

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
