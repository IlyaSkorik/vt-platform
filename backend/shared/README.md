# Shared Kernel

Cross-context building blocks reused by every bounded context (ARCH-001 §14,
`shared_kernel`). The shared kernel is **not a dumping ground**: it holds only
framework-neutral primitives and integration contracts that carry **no
context-specific business logic**.

**Dependency direction:** bounded contexts (`apps/*`) may depend on `shared`;
`shared` depends on **no** bounded context. Nothing here imports from `apps/`.

## Packages

| Package | Purpose | What belongs here | What must NOT go here |
|---------|---------|-------------------|-----------------------|
| `core/` | Core building blocks shared across contexts. | Base classes and primitives with no domain rules: entity / aggregate-root / value-object base types, `Result`/error-result types, identifier helpers. | Any context's entities, policies, or business rules. |
| `exceptions/` | Shared exception hierarchy. | Base error types (e.g. `DomainError`, `ApplicationError`) and the mapping contract to RFC 9457 Problem Details at the edge (ARCH-001 §7.6, API-000 §8). | Context-specific exceptions (those live in `apps/<ctx>/domain/exceptions.py`). |
| `events/` | Shared domain-event infrastructure. | The event base contract, the transactional outbox, and the dispatcher relaying events to Redis/Celery (ARCH-001 §4.8, §7.4). | Concrete business events (those live in `apps/<ctx>/domain/events.py`). |
| `utils/` | Framework-neutral helpers. | Small, dependency-light utilities: UUID v7 generation, time/clock helpers (API-000 §22, §23), pagination-cursor codecs. | Anything importing Django, DRF, or a context. Business logic. |
| `types/` | Shared typing helpers. | Common type aliases and `Protocol`s that keep the domain and application layers strongly typed (ARCH-001 §26.1). | Runtime behaviour or business rules. |

## Rules

- Keep it small and stable — additions require justification; the shared kernel
  is a shared coupling point.
- Framework-free by default. Only `events/` and `utils/` may touch infrastructure
  concerns (outbox/dispatcher, Celery relay), and even then behind narrow contracts.
- If something is meaningful to **one** context only, it belongs in that context,
  not here.
