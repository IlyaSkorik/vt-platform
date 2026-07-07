"""Domain exceptions for the Participants bounded context.

Purpose
    Typed, framework-free domain errors raised by this context's value objects,
    entities, services, and policies — value-object validation failures, illegal
    aggregate-state transitions, and policy violations. They are the domain's own
    error vocabulary, later translated by the application layer and mapped to
    RFC 9457 Problem Details at the presentation edge (ARCH-001 §7.6).

Layer responsibility
    Signalling only. Domain errors describe *what rule was broken*; they carry no
    HTTP status, DRF detail, or transport concern. The hierarchy is intentionally
    shallow, rooted in a single context base error.

Dependency rules
    Standard library only — no Django or DRF imports. Imported by the sibling
    domain modules that raise them; must not import ``application``,
    ``infrastructure``, or ``presentation``.

Structure only at bootstrap — no exception types defined yet.
"""
