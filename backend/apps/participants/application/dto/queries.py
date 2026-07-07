"""Query DTOs for the Participants bounded context.

Purpose
    Input criteria and result shapes for the read use cases in
    :mod:`apps.participants.application.queries` — the framework-neutral request
    filters and response projections returned to callers.

Layer responsibility
    Transport-agnostic data carriers only: no business rules, no persistence, no
    serializer or ORM types.

Dependency rules
    Standard library only — no Django or DRF. May reference this context's
    ``domain`` value types; must not import ``infrastructure`` or
    ``presentation``.

Structure only at bootstrap — no query DTOs defined yet.
"""
