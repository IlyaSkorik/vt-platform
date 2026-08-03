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
| [OPS-001](OPS-001-deploy-runbook.md) | Deployment runbook (single server) | Active |
| [OPS-007](OPS-007-object-storage.md) | Object storage for uploads and generated documents | Active |
| [OPS-008](OPS-008-single-server-sizing.md) | Single-server sizing & tuning (PostgreSQL, gunicorn, Celery, Redis, nginx) | Active |
| [OPS-009](OPS-009-mail-provider-quotas.md) | Mail provider quotas and how the platform stays inside them | Active |

> Infrastructure, Docker, CI/CD, logging, monitoring, backup, DR, and deployment are defined in [ARCH-001 §16–§25](../architecture/ARCH-001-vt-platform-architecture.md#16-infrastructure) and [§29](../architecture/ARCH-001-vt-platform-architecture.md#29-deployment-strategy).

## Future Documents

- `OPS-002` — Docker & container strategy. The images themselves are in place
  (`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.prod.yml`); what is unwritten is
  the reasoning behind them as a document.
- `OPS-003` — CI/CD pipeline. Implemented in `.github/workflows/ci.yml` and `deploy.yml`; the
  deployment half is described in [OPS-001](OPS-001-deploy-runbook.md).
- `OPS-004` — Observability (logging, metrics, tracing, alerting).
- `OPS-005` — Backup & disaster-recovery runbooks.
- `OPS-006` — Incident-response & on-call runbooks.
