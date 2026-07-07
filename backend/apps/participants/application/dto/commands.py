"""Command DTOs for the Participants bounded context.

Purpose
    Input shapes for the state-changing use cases in
    :mod:`apps.participants.application.commands` — the framework-neutral request
    payloads (e.g. register-participant, link-guardian) that a use case consumes.

Layer responsibility
    Transport-agnostic data carriers only: no business rules, no persistence, no
    serializer or ORM types. Validation of *format* belongs to the presentation
    edge; validation of *invariants* belongs to the domain.

Dependency rules
    Standard library only — no Django or DRF. May reference this context's
    ``domain`` value types; must not import ``infrastructure`` or
    ``presentation``.

Structure only at bootstrap — no command DTOs defined yet.
"""
