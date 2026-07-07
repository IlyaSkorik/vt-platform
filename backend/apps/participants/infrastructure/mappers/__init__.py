"""Domain <-> persistence mappers for the Participants bounded context.

Purpose
    Translate between the framework-free domain objects and the Django ORM
    models, keeping the domain ignorant of persistence (ARCH-001 §4.1, §7.2).

Layer responsibility
    The sole Anti-Corruption Layer permitted to know both the domain aggregates
    and the ORM models; nothing else crosses that boundary. Mappers hold no
    business rules — they reconstruct aggregates from rows and flatten aggregates
    into rows.

Dependency rules
    May import this context's ORM models and ``domain`` types. Used by the
    repositories; must not import ``application`` use cases or ``presentation``.

Structure only at bootstrap — no mappers defined yet.
"""
