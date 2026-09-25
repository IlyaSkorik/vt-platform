# VT Platform support bot image — multi-stage build, same shape as backend/Dockerfile.
# One process, no web server, no database client: this image exists to hold a polling loop.

# --- Stage 1: build dependencies into a virtual environment ---------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Stage 2: lean runtime ------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# No libpq package: `psycopg[binary]` ships its own, and this image has nothing else that needs
# one. Conversations live in the platform's Postgres, so the container itself holds no state.
RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY support_bot ./support_bot

USER app

CMD ["python", "-m", "support_bot"]
