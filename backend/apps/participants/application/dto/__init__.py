"""Data-transfer objects for the Participants application layer.

Purpose
    Plain, serialization-agnostic input/output shapes that cross the use-case
    boundary, split into command DTOs (:mod:`.commands`) and query DTOs
    (:mod:`.queries`). They decouple use cases from any particular transport, so
    the same handler can be driven by DRF, a CLI, or a task.

Layer responsibility
    Carry data only — no behaviour, no validation of business rules (that is the
    domain's job), no ORM or serializer types.

Dependency rules
    Standard library only — no Django or DRF. May reference this context's
    ``domain`` value types; must not import ``infrastructure`` or
    ``presentation``.

Structure only at bootstrap — no DTOs defined yet.
"""
