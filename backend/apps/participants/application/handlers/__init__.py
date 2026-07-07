"""Domain-event handlers for the Participants bounded context.

Purpose
    React to domain events — raised within this context or received from other
    contexts (ARCH-001 §4.8) — to run follow-up work such as provisioning a
    profile after a participant is registered or re-evaluating activation when a
    guardian relationship is verified. Handlers are the subscribing counterpart
    to the facts produced in :mod:`apps.participants.domain.events`.

Layer responsibility
    Thin orchestrators triggered by events; they invoke command/query use cases
    or ports and hold no business rules. Whether a handler runs inline or via an
    outbox/worker is decided at composition time.

Dependency rules
    Depends only on this context's ``domain`` and the application's own
    ``interfaces``/``dto``/``commands``/``queries``. Must not import
    ``infrastructure`` or ``presentation``, nor any Django/DRF symbol.

Structure only at bootstrap — no handlers defined yet.
"""
