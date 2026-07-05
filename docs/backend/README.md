# Backend Documentation

## Purpose

Engineering documentation for the backend: Django 6 + DRF modular monolith, its Clean Architecture layering, module (bounded-context) structure, persistence, background processing, and backend conventions.

## Scope

- **In scope:** module structure & boundaries, layering rules (interface → application → domain → infrastructure), persistence & migration strategy, Celery/async processing, transactional outbox & events, backend coding standards, and local setup guides.
- **Out of scope:** API contracts (see [../api](../api/README.md)) and infrastructure/deployment (see [../devops](../devops/README.md)).

## Prefix

Documents in this domain use the `BE-` prefix (e.g. `BE-001-module-structure.md`).

## Documents

| ID | Title | Status |
|----|-------|--------|
| — | _No documents yet._ | — |

> The backend architecture and Django app structure are defined in [ARCH-001 §7](../architecture/ARCH-001-vt-platform-architecture.md#7-backend-architecture) and [§14](../architecture/ARCH-001-vt-platform-architecture.md#14-django-apps-structure).

## Future Documents

- `BE-001` — Module & bounded-context structure.
- `BE-002` — Clean Architecture layering & dependency rules.
- `BE-003` — Persistence, migrations & schema-per-context.
- `BE-004` — Celery, events & the transactional outbox.
- `BE-005` — Backend coding standards & local development guide.
