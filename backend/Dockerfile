# VT Platform backend image — multi-stage build (ARCH-001 §17).
# One process type per container; non-root runtime; small final image.

# --- Stage 1: build dependencies into a virtual environment ---------------
FROM python:3.13-slim AS builder

# uv provides fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer), then the project metadata.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# --- Stage 2: lean runtime ------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# libpq for psycopg runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . /app

USER app

EXPOSE 8000

# API served under ASGI (Uvicorn workers under Gunicorn). Worker/beat images
# reuse this image with a different entrypoint (ARCH-001 §17.2).
CMD ["gunicorn", "config.asgi:application", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3"]
