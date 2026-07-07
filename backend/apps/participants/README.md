# Participants bounded context

Domain 2 of the VT Platform («Взлёт талантов») — **Core** (DATA-001 §3.4, §4.2).

## Purpose

Owns the **subjects of the platform** and the adults authorised to act for them,
with strict **data minimization** (ARCH-001 §21.6). Children generally do **not**
hold independent accounts (their `User Account` lives in *Identity*); they are
represented here as **Participants** and acted for by verified **Guardians** or
authorised **Teachers/Institutions** with recorded consent (DATA-001 §3.4).

Business objects in scope (DATA-001 §4.2): Participant, Guardian, Teacher,
Guardian Relationship, Teacher Relationship, the corresponding profiles,
Participant Institution Membership, Participant Group Membership, Participant
Portfolio, and Talent Interest.

Representative invariants this context will enforce (DATA-002): a participant must
be linked to at least one **verified** guardian *or* an authorised
institution/teacher with recorded consent before becoming **Active**; a guardian
may manage only participants to whom a **verified** relationship exists; the age
group is **derived** from date of birth, never client-supplied; a **display
alias** enables pseudonymized judging.

> **Status:** architectural skeleton only. No entities, value objects, events,
> policies, ORM models, repositories, DTOs, handlers, or endpoints are defined
> yet — every module carries documentation and structure, nothing more.

## Layered architecture (ARCH-001 §7.2)

```
participants/
├── domain/          # framework-free business core (entities, VOs, events, policies, services, ports, errors)
├── application/     # use cases: commands, queries, handlers, DTOs, ports, error vocabulary
├── infrastructure/  # adapters: ORM models, repositories, mappers, admin, migrations
└── presentation/    # REST edge: versioned API surface (api/v1)
```

## Dependency rules (never violated)

```
Domain  ←  Application  ←  Infrastructure  ←  Presentation
```

Dependencies point **inward**. The `domain` layer depends on nothing but the
standard library. `application` depends only on `domain`. `infrastructure` and
`presentation` depend on the inner layers and are injected at composition time
(ARCH-001 §7.3, Dependency Inversion) — the inner layers never import outward.

Cross-context references are held as **IDs** and resolved through the owning
context's public interface; this context never imports another app's ORM models
(ARCH-001 §9.2, §14). It maps to its own `participants` PostgreSQL schema.
