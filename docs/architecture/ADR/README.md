# Architecture Decision Records (ADR)

## What is an ADR?

An **Architecture Decision Record** captures a single, significant architectural decision — the context that forced the decision, the decision itself, the alternatives considered, and the consequences. ADRs give the team a durable, honest history of *why* the system is the way it is, so future engineers can change it with full understanding rather than guesswork.

We follow the **MADR** (Markdown Any Decision Records) convention.

## Purpose

- Make architectural reasoning **explicit and reviewable**.
- Prevent silent erosion of the architecture principles (see [ARCH-001 §4](../ARCH-001-vt-platform-architecture.md#4-architecture-principles)).
- Provide traceability from principle → decision → consequence.

## Scope

Any decision that:

- changes or reinforces an architecture principle,
- affects a cross-cutting concern (auth, data, security, deployment),
- selects or replaces a core technology, or
- establishes a boundary (bounded context, module, service extraction),

**must** be recorded as an ADR and referenced from the pull request that implements it.

## Rules

- **Naming:** `ADR-NNNN-slug.md` (4-digit, zero-padded, e.g. `ADR-0001-modular-monolith.md`).
- **Immutable:** once `Accepted`, an ADR is not edited. To change a decision, write a new ADR and set the old one to `Superseded by ADR-XXXX`.
- **Numbering:** sequential and never reused.
- **Status lifecycle:** `Proposed → Accepted → (Deprecated | Superseded)`.

## Template

```markdown
# ADR-NNNN — <Title>

- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
- **Date:** YYYY-MM-DD
- **Deciders:** <names / roles>

## Context
What is the problem, and what forces (technical, business, organizational) apply?

## Decision
The decision, stated in active voice: "We will …".

## Alternatives Considered
Options evaluated and why they were not chosen.

## Consequences
Positive, negative, and neutral outcomes. What becomes easier, and what becomes harder.
```

## Baseline Decision Register

The full v1.0 decision register lives inline in **[ARCH-001 §30](../ARCH-001-vt-platform-architecture.md#30-architecture-decision-records-adr)** (ADR-0001 … ADR-0013). As those decisions are revisited or extended, each is promoted into its own file in this directory and indexed below.

| ADR | Title | Status |
|-----|-------|--------|
| — | _No standalone ADR files yet; see ARCH-001 §30 for the baseline register._ | — |

## Future Documents

- Individual `ADR-0001 … ADR-0013` files extracted from the ARCH-001 baseline register.
- New ADRs as architectural decisions are made.
