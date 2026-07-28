# DevOps Documentation

## Purpose

Documentation for how the platform is built, shipped, run, observed, and recovered: infrastructure topology, containerization, CI/CD, observability, and operational runbooks.

## Scope

- **In scope:** infrastructure & environments, Docker/container strategy, CI/CD pipelines (GitHub Actions), deployment strategy, logging/monitoring, backup & disaster-recovery procedures, and on-call runbooks.
- **Out of scope:** application source and product/business docs.

## Prefix

Documents in this domain use the `OPS-` prefix (e.g. `OPS-001-environments.md`).

## Documents

| ID | Title | Status |
|----|-------|--------|
| [OPS-007](OPS-007-object-storage.md) | Object storage for uploads and generated documents | Active |

> Infrastructure, Docker, CI/CD, logging, monitoring, backup, DR, and deployment are defined in [ARCH-001 §16–§25](../architecture/ARCH-001-vt-platform-architecture.md#16-infrastructure) and [§29](../architecture/ARCH-001-vt-platform-architecture.md#29-deployment-strategy).

## Future Documents

- `OPS-001` — Environments & configuration.
- `OPS-002` — Docker & container strategy.
- `OPS-003` — CI/CD pipeline (GitHub Actions).
- `OPS-004` — Observability (logging, metrics, tracing, alerting).
- `OPS-005` — Backup & disaster-recovery runbooks.
- `OPS-006` — Incident-response & on-call runbooks.
- `OPS-008` — Single-server sizing & tuning (Postgres, gunicorn, Celery, Redis).
