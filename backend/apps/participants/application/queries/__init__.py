"""Query use cases for the Participants bounded context.

Purpose
    The **read side**: side-effect-free operations that return DTOs describing
    participants, guardians, teachers, and their relationships/memberships. Kept
    separate from commands so reads never mutate state (ARCH-001 §7.2, §7.4).

Layer responsibility
    Retrieve via the injected repository ports and shape results into query DTOs.
    No business rules and no transport concerns.

Dependency rules
    Depends only on this context's ``domain`` and the application's own
    ``interfaces``/``dto``. Must not import ``infrastructure`` or
    ``presentation``, nor any Django/DRF symbol.

Structure only at bootstrap — no queries defined yet.
"""
