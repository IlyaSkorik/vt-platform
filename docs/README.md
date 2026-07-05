# VT Platform — Documentation

Central documentation hub for **«Взлёт талантов»** — the digital ecosystem for organizing children's creative competitions.

This directory is the single source of truth for all project documentation: architecture, business, API, engineering, DevOps, AI, roadmap, and diagrams. Source code lives elsewhere; **this tree is documentation only**.

---

## 1. Purpose

- Provide one authoritative, navigable home for every project document.
- Enforce a consistent **numbering and naming scheme** so documents are stable, referenceable, and never ambiguous.
- Give every contributor a predictable map of *where a document belongs* and *where to find it*.

## 2. Scope

- **In scope:** architecture, decisions (ADRs), business/domain docs, API contracts and guidelines, backend/frontend engineering docs, DevOps/runbooks, AI usage and prompts, roadmap, and diagrams.
- **Out of scope:** application source code, build artifacts, secrets, and third-party generated output.

---

## 3. Documentation Map

```
docs/
├── README.md                  ← you are here (index + numbering + map)
├── architecture/              ARCH-*  System & technical architecture
│   ├── ARCH-001-vt-platform-architecture.md
│   └── ADR/                   ADR-*   Architecture Decision Records
├── business/                  BUS-*   Vision, goals, domain, stakeholders
├── api/                       API-*   API contracts, standards, versioning
├── backend/                   BE-*    Backend engineering docs
├── frontend/                  FE-*    Frontend engineering docs
├── devops/                    OPS-*   Infra, CI/CD, runbooks, operations
├── ai/                        AI-*    AI usage, governance, prompts
│   └── prompts/               Reusable, versioned prompt library
├── roadmap/                   RM-*    Product & technical roadmap
└── diagrams/                  DIA-*   Visual models
    ├── c4/                    System context / container / component
    ├── erd/                   Entity-relationship diagrams
    ├── sequence/              Sequence & flow diagrams
    ├── bpmn/                  Business process models
    └── ui/                    UI wireframes & mockups
```

---

## 4. Document Numbering

Every substantive document carries a **domain prefix + zero-padded sequence number** and a kebab-case slug:

```
<PREFIX>-<NNN>-<slug>.md
```

Example: `ARCH-001-vt-platform-architecture.md`, `ADR-0001-modular-monolith.md`.

| Prefix | Domain | Directory |
|--------|--------|-----------|
| `ARCH` | Architecture | `docs/architecture/` |
| `ADR`  | Architecture Decision Records | `docs/architecture/ADR/` |
| `BUS`  | Business & domain narrative | `docs/business/` |
| `DATA` | Business domain & data model | `docs/business/` |
| `API`  | API design & contracts | `docs/api/` |
| `BE`   | Backend engineering | `docs/backend/` |
| `FE`   | Frontend engineering | `docs/frontend/` |
| `OPS`  | DevOps & operations | `docs/devops/` |
| `AI`   | AI usage & governance | `docs/ai/` |
| `RM`   | Roadmap | `docs/roadmap/` |
| `DIA`  | Diagrams | `docs/diagrams/` |

**Rules**
- Numbers are **immutable once assigned** and never reused, even if a document is superseded (mark it `Superseded by …` instead of deleting the number).
- ADRs use a 4-digit sequence (`ADR-0001`); all other domains use 3 digits (`ARCH-001`).
- Slugs are lowercase, hyphen-separated, and stable.

---

## 5. Documentation Index

| ID | Title | Status | Location |
|----|-------|--------|----------|
| ARCH-001 | VT Platform Architecture v1.0 | Approved | [architecture/ARCH-001-vt-platform-architecture.md](architecture/ARCH-001-vt-platform-architecture.md) |
| DATA-001 | Business Data Model v1.0 | Draft for review | [business/DATA-001-business-data-model.md](business/DATA-001-business-data-model.md) |
| DATA-002 | Business Rules Catalog v1.0 | Draft for review | [business/DATA-002-business-rules-catalog.md](business/DATA-002-business-rules-catalog.md) |

> Additional documents are registered here as they are authored. Each README in a subdirectory maintains its own local index of that domain's documents.

---

## 6. Domain Indexes

| Domain | README |
|--------|--------|
| Architecture | [architecture/README.md](architecture/README.md) |
| ADR | [architecture/ADR/README.md](architecture/ADR/README.md) |
| Business | [business/README.md](business/README.md) |
| API | [api/README.md](api/README.md) |
| Backend | [backend/README.md](backend/README.md) |
| Frontend | [frontend/README.md](frontend/README.md) |
| DevOps | [devops/README.md](devops/README.md) |
| AI | [ai/README.md](ai/README.md) |
| Roadmap | [roadmap/README.md](roadmap/README.md) |
| Diagrams | [diagrams/README.md](diagrams/README.md) |

---

## 7. Conventions

- **Format:** GitHub-Flavored Markdown, UTF-8, one sentence-per-line encouraged for clean diffs.
- **Language:** English for technical content; Russian domain terms preserved where meaningful.
- **Cross-references:** always relative links within `docs/`.
- **Contributions:** see the root [CONTRIBUTING.md](../CONTRIBUTING.md).

## 8. Future Documents

- A generated, machine-readable documentation index (e.g. `docs/index.json`).
- A static documentation site (MkDocs / Docusaurus) built from this tree in CI.
- Templates directory (`docs/_templates/`) for each document type.
