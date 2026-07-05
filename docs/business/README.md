# Business Documentation

## Purpose

Capture *what* the platform is for and *who* it serves: product vision, business goals, stakeholders, domain language, and the rules that shape the product independent of any technical implementation.

## Scope

- **In scope:** vision, business goals & KPIs, stakeholder/actor definitions, ubiquitous language & glossary, the **business domain & data model**, business processes, monetization model, and compliance/regulatory context (e.g. 152-ФЗ).
- **Out of scope:** technical architecture (see [../architecture](../architecture/README.md)) and API/engineering details.

## Prefix

Business narrative documents use the `BUS-` prefix (e.g. `BUS-001-vision-and-goals.md`). The business **data model** uses the dedicated `DATA-` prefix (e.g. `DATA-001-business-data-model.md`), as it is a distinct, cross-cutting reference artifact.

## Documents

| ID | Title | Status |
|----|-------|--------|
| DATA-001 | [Business Data Model v1.0](DATA-001-business-data-model.md) | Draft for review |
| DATA-002 | [Business Rules Catalog v1.0](DATA-002-business-rules-catalog.md) | Draft for review |
| DATA-003 | [Domain Event Catalog v1.0](DATA-003-domain-event-catalog.md) | Draft for review |

> The current vision and business goals are summarized in [ARCH-001 §1–§2](../architecture/ARCH-001-vt-platform-architecture.md#1-vision); standalone business documents will expand and own these. The business domain, objects, aggregates, and value objects are defined in **DATA-001**; the complete catalogue of business rules (invariants, workflows, permissions, calculations, disclosures, compliance) is defined in **DATA-002**; the catalogue of significant business events (with dependency graph, cross-domain flow, ownership, and versioning) is defined in **DATA-003**.

## Future Documents

- `BUS-001` — Vision & business goals.
- `BUS-002` — Stakeholders & actors.
- `BUS-003` — Ubiquitous language & glossary.
- `BUS-004` — Competition lifecycle & business rules.
- `BUS-005` — Monetization & pricing model.
- `BUS-006` — Data-privacy & compliance obligations (minors, 152-ФЗ).
