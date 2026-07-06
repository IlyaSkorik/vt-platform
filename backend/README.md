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
        ┌──────────────────────────────────────────────────────────┐
        │  presentation/   api/v1/<resource>/                        │  HTTP edge only
        │                  serializers · views · permissions · urls  │
        ├──────────────────────────────────────────────────────────┤
        │  application/    commands · queries · handlers             │  use cases
        │                  dto/ (commands, queries) · interfaces     │  (ports)
   dependencies  ────────────────────────────────────────────────────
   point inward  │  domain/  entities · value_objects · events        │  framework-free
        ▼         │           services · policies · exceptions         │  business core
        │         │           interfaces (domain ports)                │
        ├──────────────────────────────────────────────────────────┤
        │  infrastructure/ models/ · repositories/ · mappers/        │  adapters
        │                  admin · migrations/                       │  (persistence, IO)
        └──────────────────────────────────────────────────────────┘
```

### Layer responsibilities

- **`domain/`** — the framework-free business core. Imports **nothing** from Django, DRF,
  or infrastructure.
  - `entities.py` — aggregates/entities with identity and their invariants.
  - `value_objects.py` — immutable, identity-less concepts (Money, AgeGroup, …).
  - `services.py` — domain services: business behaviour spanning aggregates that fits no
    single entity.
  - `policies.py` — explicit, testable business policies/invariants
    (`JudgeAssignmentPolicy`, `CompetitionEligibilityPolicy`, `AgeCategoryPolicy`).
  - `events.py` — past-tense domain events (the integration currency, ARCH-001 §4.8).
  - `exceptions.py` — typed domain errors.
  - `interfaces.py` — domain-owned ports (repository/gateway protocols).
- **`application/`** — orchestrates one business operation per use case, owns the
  transaction boundary, publishes events.
  - `commands/`, `queries/`, `handlers/` — write use cases, read use cases, event handlers.
  - `dto/` — framework-neutral input/output shapes: `commands.py`, `queries.py`.
  - `interfaces.py` — the ports use cases depend on (`UserRepository`, `EmailGateway`,
    `NotificationGateway`, `Clock`, `EventBus`); concrete adapters are injected.
- **`infrastructure/`** — adapters implementing the ports.
  - `models/` — Django ORM models (package, so they split per aggregate as a context grows).
  - `repositories/` — ORM-backed repository implementations.
  - `mappers/` — translation between domain objects and ORM models.
  - `admin.py`, `migrations/` — operational surface and per-context schema migrations.
- **`presentation/`** — the HTTP edge only (routing, DRF serializers, permissions,
  pagination). `api/v1/<resource>/` versions the surface (API-000 §2). No business logic.

**Binding rules (ARCH-001 §7, §26.1; enforced by review):**

- Business logic MUST NEVER live in Django models, serializers, views, admin, or signals.
- **Use cases** belong only to `application/`.
- **Business rules** belong only to `domain/` (which imports nothing from Django).
- **Persistence** belongs only to `infrastructure/`.
- **REST** belongs only to `presentation/`.
- Concrete adapters are injected at composition time (Dependency Inversion).
- No context imports another context's ORM models — only its published interface.

### Dependency direction

Dependencies point **inward only** (ARCH-001 §4.1, §7.3):

```
presentation ─┐
              ├─▶ application ─▶ domain      (domain depends on nothing)
infrastructure ┘        ▲            ▲
                        └── implements ports defined by application & domain
```

- `domain` depends on nothing (not even `shared` framework code — only pure primitives).
- `application` depends on `domain` and on **its own port interfaces** — never on
  `infrastructure` or `presentation`.
- `infrastructure` and `presentation` depend inward on `application`/`domain`;
  `infrastructure` **implements** the ports, wired at composition time.
- An import that points **outward** (e.g. `domain` importing a Django model) is an
  architecture violation.

### Why business logic must never live in Django Models, Views, or Serializers

The dependency rule above exists to protect the business core. Concretely:

- **Models are a persistence detail.** A Django model is an adapter to PostgreSQL. Rules
  encoded in `save()`, `clean()`, signals, or custom managers are welded to the ORM — they
  cannot be unit-tested without a database, cannot be reused off the HTTP/ORM path (Celery
  workers, imports, other contexts), and leak schema concerns into decisions. Business rules
  live in `domain/` (entities, `services.py`, `policies.py`) as plain Python, tested with no
  database (ARCH-001 §28.2) and reused everywhere.
- **Serializers are a transport detail.** They validate and shape JSON at the edge. Rules
  placed there apply only to that one endpoint and silently bypass any other caller; edge
  validation (shape) is not the same as a domain invariant (truth). Invariants belong in the
  domain and are re-checked in the application layer.
- **Views are an HTTP detail.** A view parses a request, invokes **one** use case, and maps
  the result to a response (including RFC 9457 errors). Orchestration and transaction
  boundaries belong in `application/`; putting them in views ties workflow to HTTP and makes
  the same operation impossible to trigger from a task or CLI.

Keeping frameworks at the edges makes the domain **testable, reusable, and replaceable** —
infrastructure (ORM, DRF, even Django) can change without touching business rules, and hot
contexts can later be extracted into their own service with minimal blast radius
(ARCH-001 §4.1, §23.5, §31).

### Bounded contexts

`identity` · `participants` · `institutions` · `competitions` · `applications` ·
`performances` · `judging` · `results` · `finance` · `notifications` · `analytics` ·
`audit` — mapped to the twelve business domains of
[`DATA-001 §3`](../docs/business/DATA-001-business-data-model.md#3-domain-overview). Each
context maps to its own PostgreSQL schema (ARCH-001 §9.2).

Every context exposes its REST surface under `presentation/api/v1/`. The **identity**
context — the only one with a ratified API contract
([`API-001`](../docs/api/API-001-identity.md)) — carries resource packages `auth/`,
`users/`, `sessions/`, and `permissions/`; other contexts hold the empty versioned `api/v1/`
container, to be populated as their API contracts (`API-002+`) are designed. Structure only:
no serializers, views, routes, or endpoints exist yet.

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
├── shared/                     # shared kernel (no business logic) — see shared/README.md
│   ├── README.md               # purpose of every shared package
│   ├── core/                   # base entity/aggregate/value-object/result types
│   ├── exceptions/             # base error hierarchy → RFC 9457 mapping
│   ├── events/                 # domain-event base, transactional outbox, dispatcher
│   ├── utils/                  # framework-neutral helpers (UUID v7, time)
│   └── types/                  # shared typing helpers
├── apps/                       # one package per bounded context
│   └── <context>/
│       ├── apps.py             # AppConfig
│       ├── domain/             # entities · value_objects · events · services
│       │                       #   · policies · exceptions · interfaces
│       ├── application/
│       │   ├── commands/       # write use cases
│       │   ├── queries/        # read use cases
│       │   ├── handlers/       # domain-event handlers
│       │   ├── dto/            # commands.py, queries.py
│       │   └── interfaces.py   # ports required by use cases
│       ├── infrastructure/
│       │   ├── models/         # Django ORM models (package)
│       │   ├── repositories/   # repository implementations (package)
│       │   ├── mappers/        # domain <-> ORM mapping
│       │   ├── admin.py
│       │   └── migrations/
│       └── presentation/
│           └── api/v1/         # versioned REST surface (resource packages)
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
