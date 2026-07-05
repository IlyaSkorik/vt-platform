# Diagrams

## Purpose

Hold the platform's visual models — the pictures that make the architecture, data, flows, processes, and UI understandable at a glance. Diagrams complement the written docs; they never replace them.

## Scope

- **In scope:** C4 model diagrams, entity-relationship diagrams, sequence/flow diagrams, BPMN business processes, and UI wireframes/mockups.
- **Out of scope:** prose documentation (lives in the sibling `docs/` domains).

## Prefix

Diagram documents use the `DIA-` prefix where a wrapping document is needed (e.g. `DIA-001-c4-context.md`).

## Documents

| ID | Title | Status |
|----|-------|--------|
| DIA-001 | [Entity Relationship Model v1.0 (Logical Data Model)](DIA-001-entity-relationship-model.md) | Draft for review |

> **DIA-001** is the logical data model (entities, relationships, cardinality, aggregates, integrity/deletion/history/audit strategies) with embedded Mermaid ER diagrams. It realizes the business objects of [DATA-001](../business/DATA-001-business-data-model.md) and defers physical schema to [ARCH-001 §9](../architecture/ARCH-001-vt-platform-architecture.md#9-database-architecture).

## Structure

| Directory | Contents |
|-----------|----------|
| [`c4/`](c4/) | C4 model: system context, container, component diagrams |
| [`erd/`](erd/) | Entity-relationship diagrams (per bounded context) |
| [`sequence/`](sequence/) | Sequence & flow diagrams for key use cases |
| [`bpmn/`](bpmn/) | BPMN models of business processes (competition lifecycle, judging) |
| [`ui/`](ui/) | UI wireframes & mockups (mobile-first) |

## Conventions

- **Diagrams as code preferred:** use text-based, version-controllable formats (Mermaid, PlantUML, Structurizr DSL) so diagrams diff and review cleanly. Exported images (SVG/PNG) may accompany the source but the source is authoritative.
- **Naming:** `<area>-<NNN>-<slug>.<ext>` within each subdirectory.
- **Traceability:** each diagram references the doc/section it illustrates.

## Future Documents

- `c4/` — Context, container, and component diagrams (source for [ARCH-001 §5](../architecture/ARCH-001-vt-platform-architecture.md#5-high-level-architecture)).
- `erd/` — Per-context entity-relationship diagrams extracted from **DIA-001**.
- `sequence/` — Registration, submission-upload, and judging flows.
- `bpmn/` — Competition lifecycle & judging processes.
- `ui/` — Mobile-first wireframes for core journeys.
