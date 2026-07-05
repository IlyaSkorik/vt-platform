# Architecture Documentation

System and technical architecture for the VT Platform.

## Purpose

Describe *how* the platform is built and *why*: the structural decisions, layering, technology choices, cross-cutting concerns, and the reasoning that ties them to business and non-functional requirements.

## Scope

- **In scope:** high-level and detailed architecture, technology stack, layering (Clean Architecture / DDD), infrastructure topology, security/privacy posture, scalability, and the ADR log that records binding decisions.
- **Out of scope:** business goals in isolation (see [../business](../business/README.md)), API endpoint contracts (see [../api](../api/README.md)), and implementation code.

## Documents

| ID | Title | Status |
|----|-------|--------|
| ARCH-001 | [VT Platform Architecture v1.0](ARCH-001-vt-platform-architecture.md) | Approved baseline |

Architecture decisions are recorded separately as ADRs — see **[ADR/README.md](ADR/README.md)**.

## Future Documents

- `ARCH-002` — Detailed judging-subsystem design.
- `ARCH-003` — Media pipeline (upload, scanning, transcoding, delivery) design.
- `ARCH-004` — Event catalogue & integration contracts.
- `ARCH-005` — Multi-region / DR reference architecture.
