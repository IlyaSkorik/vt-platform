"""ORM models (adapters) for the Participants bounded context.

Purpose
    The database representation of this context's aggregates and entities. Django
    models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and carry NO
    business logic — the domain layer remains the source of truth, and the
    mapper/repository reads from and writes to these classes.

Layer responsibility
    Persistence shape only. A package (not a single module) so models can be
    split per aggregate as the context grows. This context maps to its own
    ``participants`` PostgreSQL schema (ARCH-001 §9.2); table names carry the
    ``participants_`` context prefix.

Dependency rules
    May import Django ORM. Depends inward on ``domain`` types only where a field
    needs them; must not import ``application`` use cases or ``presentation``.
    Discovered via :meth:`apps.participants.apps.ParticipantsConfig.ready`, since
    models are not in the default ``<app>/models.py``.

No models are defined during bootstrap.
"""
