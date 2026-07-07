"""Application ports (contracts) required by Participants use cases.

Purpose
    The **outbound dependencies** of the Participants application layer, expressed
    as pure structural seams (ARCH-001 §7.3, Dependency Inversion). Use cases will
    depend on abstractions such as a participant/guardian/teacher repository, an
    injected clock and identifier generator, and an event publisher; the concrete
    adapters (a Django ORM repository, a UUID v7 generator, an outbox publisher)
    live in ``infrastructure/`` and are injected at composition time.

Layer responsibility
    Interfaces only — no implementations. Each port is fully typed and uses no
    ``Any``. The dependency arrow points *inward*: infrastructure depends on this
    module, never the reverse.

Dependency rules
    Standard library only — no Django, DRF, ORM, message bus, or IO. May import
    this context's ``domain`` types; must not import ``infrastructure`` or
    ``presentation``.

Structure only at bootstrap — no ports defined yet.
"""
