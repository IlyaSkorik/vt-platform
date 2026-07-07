"""Domain entities for the Participants bounded context.

Purpose
    Home of this context's aggregates and entities — the framework-free business
    core that owns state and behaviour (ARCH-001 §7.2, §13.4). The intended
    aggregate roots and entities are Participant, Guardian, Teacher, their
    profiles, Guardian/Teacher Relationships, Participant Institution/Group
    Memberships, Participant Portfolio, and Talent Interest (DATA-001 §4.2). Each
    aggregate will guard its own invariants (e.g. a participant becomes Active
    only once a verified guardian or authorised institution/teacher with recorded
    consent exists — DATA-002) and derive age group from date of birth rather
    than trusting client input, in line with strict data minimization
    (ARCH-001 §21.6).

Layer responsibility
    Pure business rules and state transitions. Entities validate invariants and
    return the domain events they produce; they never persist themselves, render
    themselves, or read a global clock — time and identity are supplied by the
    caller so aggregates stay deterministic and testable.

Dependency rules
    Standard library only — no Django, DRF, ORM, or infrastructure. May import
    sibling domain modules (:mod:`value_objects`, :mod:`events`, :mod:`policies`,
    :mod:`exceptions`) but nothing from ``application``, ``infrastructure``, or
    ``presentation``. This is the innermost layer; the dependency arrow always
    points toward it.

Structure only at bootstrap — no entities defined yet.
"""
