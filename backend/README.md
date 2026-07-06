# VT Platform — Backend

Backend for **«Взлёт талантов» (VT Platform)** — a digital ecosystem for organizing
children's creative competitions.

This repository is the **backend foundation**: a Django 6 + DRF **modular monolith**
built on **Clean Architecture** and **Domain-Driven Design**. It is the source-of-truth
implementation of the decisions in [`docs/architecture/ARCH-001`](../docs/architecture/ARCH-001-vt-platform-architecture.md),
the API standard [`docs/api/API-000`](../docs/api/API-000-rest-api-standards.md), and the
business model in [`docs/business`](../docs/business).

> **Bootstrap status.** This is the infrastructure foundation only. The bounded-context
> layers exist as structured, documented placeholders — there are intentionally **no**
> ORM models, serializers, viewsets, endpoints, migrations, or business logic yet.

---

## 1. Architecture

The backend is a **modular monolith** (ARCH-001 §4.9, §7): a single deployable Django
application internally partitioned into **bounded contexts**. Each context follows strict
**Clean Architecture** layering — dependencies point **inward**, and the domain knows
nothing about Django, DRF, PostgreSQL, or HTTP.

```
┌───────────────────────────────────────────────┐
│  presentation/   DRF views, serializers, urls   │  HTTP edge — no business logic
├───────────────────────────────────────────────┤
│  application/    use cases, handlers, DTOs      │  orchestration, transactions, events
├───────────────────────────────────────────────┤
│  domain/         entities, value objects, rules │  framework-free business core
├───────────────────────────────────────────────┤
│  infrastructure/ ORM models, repositories       │  adapters (persistence, gateways)
└───────────────────────────────────────────────┘
```

**Binding rules (ARCH-001 §7, §26.1; enforced by review):**

- Business logic MUST NEVER live in Django models, serializers, views, admin, or signals.
- **Use cases** belong only to `application/`.
- **Business rules** belong only to `domain/` (which imports nothing from Django).
- **Persistence** belongs only to `infrastructure/`.
- **REST** belongs only to `presentation/`.
- Concrete adapters are injected at composition time (Dependency Inversion).
- No context imports another context's ORM models — only its published interface.

### Bounded contexts

`identity` · `participants` · `institutions` · `competitions` · `applications` ·
`performances` · `judging` · `results` · `finance` · `notifications` · `analytics` ·
`audit` — mapped to the twelve business domains of
[`DATA-001 §3`](../docs/business/DATA-001-business-data-model.md#3-domain-overview). Each
context maps to its own PostgreSQL schema (ARCH-001 §9.2).

---

## 2. Folder structure

```
backend/
├── config/                     # Django project: settings, urls, asgi/wsgi, celery
│   ├── settings/
│   │   ├── env.py              # strongly-typed configuration (Pydantic Settings)
│   │   ├── base.py             # shared settings
│   │   ├── development.py      # local / Docker Compose
│   │   ├── production.py       # hardened
│   │   └── testing.py          # fast, self-contained (in-memory SQLite)
│   ├── urls.py                 # schema/docs, health probes; mounts /api/v1/ routers
│   ├── asgi.py  /  wsgi.py     # ASGI is the primary serving mode
│   └── celery.py               # Celery application
├── shared/                     # shared kernel (no business logic)
│   ├── core/                   # base entity/aggregate/value-object/result types
│   ├── exceptions/             # base error hierarchy → RFC 9457 mapping
│   ├── events/                 # domain-event base, transactional outbox, dispatcher
│   ├── utils/                  # framework-neutral helpers (UUID v7, time)
│   └── types/                  # shared typing helpers
├── apps/                       # one package per bounded context
│   └── <context>/
│       ├── apps.py             # AppConfig
│       ├── domain/             # entities, value_objects, events, exceptions, interfaces
│       ├── application/        # commands/, queries/, handlers/, dto.py
│       ├── infrastructure/     # models.py, repositories.py, admin.py, migrations/
│       └── presentation/       # api/, serializers.py, views.py, permissions.py, urls.py
├── tests/                      # cross-cutting & smoke tests
├── pyproject.toml  /  uv.lock  # dependencies (managed with uv)
├── Dockerfile  /  docker-compose.yml
└── ruff.toml · mypy.ini · pytest.ini · .pre-commit-config.yaml · .editorconfig
```

---

## 3. Configuration

Configuration is **strongly typed** via **Pydantic Settings** (`config/settings/env.py`) —
`django-environ` is intentionally not used. All values are read from environment variables
(or a local `.env` for development) and validated once, then consumed by the split Django
settings modules. Select the environment with `DJANGO_SETTINGS_MODULE`
(e.g. `config.settings.development`).

Copy `.env.example` to `.env` and adjust. Defaults cover: Django (secret/debug/hosts),
localization (**timezone UTC, language `ru`**), CORS (locked to known origins), PostgreSQL,
Redis/Celery, and JWT (short-lived access + rotating refresh token).

Configured out of the box: DRF, **JWT authentication** (SimpleJWT), **CORS**
(django-cors-headers), **OpenAPI 3.1** (drf-spectacular), **static files** (WhiteNoise),
media, Argon2 password hashing, Redis cache, and Celery.

---

## 4. Development

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.13+ (uv provisions the interpreter).

```bash
# Install all dependencies (creates .venv from uv.lock)
uv sync

# Environment
cp .env.example .env

# Run the API (ASGI dev server)
uv run python manage.py runserver

# System checks
uv run python manage.py check
uv run python manage.py check --deploy   # production settings

# Tests
uv run python manage.py test             # Django test runner
uv run pytest                            # pytest (with coverage: uv run pytest --cov)

# Lint, format, type-check
uv run ruff check .
uv run ruff format .
uv run mypy config shared apps tests

# Pre-commit hooks (run the same gates as CI)
uv run pre-commit install
uv run pre-commit run --all-files

# Background workers
uv run celery -A config worker -l info
uv run celery -A config beat -l info
```

### With Docker Compose

Brings up `backend`, `worker`, `beat`, `postgres`, `redis`, `minio` (S3-compatible), and
`mailhog` for full dev/prod parity of the data, cache, queue, media, and email subsystems
(ARCH-001 §17.3):

```bash
docker compose up --build
```

### Useful endpoints

| Path | Purpose |
|------|---------|
| `/healthz` | Liveness probe |
| `/readyz` | Readiness probe |
| `/api/schema/` | OpenAPI 3.1 schema |
| `/api/schema/swagger-ui/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc |
| `/admin/` | Django admin |

---

## 5. Technology stack

Python 3.13+ · Django 6 · Django REST Framework · PostgreSQL · Redis · Celery ·
Pydantic Settings · drf-spectacular · SimpleJWT · uv · Ruff · MyPy · Pytest · Docker.

See [ARCH-001 §6](../docs/architecture/ARCH-001-vt-platform-architecture.md#6-technology-stack)
for the full stack and rationale.
