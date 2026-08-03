# VT Platform backend image — multi-stage build (ARCH-001 §17).
# One process type per container; non-root runtime; small final image.

# --- Stage 1: build dependencies into a virtual environment ---------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Build the venv OUTSIDE /app so the dev bind mount (`.:/app`) can never shadow
# it with the host's venv (which targets a host-only interpreter path).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY . .
# --- Stage 2: lean runtime ------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# libpq for psycopg runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . /app

# Bake the static manifest into the image.
#
# `STORAGES["staticfiles"]` is whitenoise's CompressedManifestStaticFilesStorage, which
# resolves every asset through `staticfiles.json`. Without that file any static lookup raises
# `ValueError: Missing staticfiles manifest entry`, so the admin, the DRF browsable API and the
# Spectacular UI all return 500 — while the JSON API stays fine and hides it.
#
# At build time rather than at start-up: the result is identical for every container from this
# image, so computing it once keeps start-up fast and makes the image self-contained.
#
# The throwaway secret is what lets production settings import here. They refuse to boot on
# the *known* development default, and rightly so — but collectstatic neither has nor needs a
# real secret, and nothing signed with this value ever leaves the build.
RUN DJANGO_SECRET_KEY="collectstatic-build-only-$(date +%s)" \
    DJANGO_ALLOWED_HOSTS="localhost" \
    python manage.py collectstatic --noinput --clear \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8000

# API served under ASGI (Uvicorn workers under Gunicorn). The sizing lives in
# `gunicorn.conf.py` (OPS-008 §4) rather than in flags here, so one place decides it.
# Worker/beat images reuse this image with a different command (ARCH-001 §17.2).
CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.asgi:application"]
