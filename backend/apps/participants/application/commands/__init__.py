"""Command use cases for the Participants bounded context.

Purpose
    The **write side**: one command = one intent to change state = one
    transaction boundary (ARCH-001 §7.2, §7.4). Commands orchestrate this
    context's aggregates and the application ports to carry out operations such
    as registering a participant, linking and verifying a guardian, or activating
    a participant.

Layer responsibility
    Thin orchestration over the domain and the injected ports; no business rules
    (those live in the domain) and no transport concerns (those live in
    presentation). Commands consume DTOs and return DTOs / results.

Dependency rules
    Depends only on this context's ``domain`` and the application's own
    ``interfaces``/``dto``/``exceptions``. Must not import ``infrastructure`` or
    ``presentation``, nor any Django/DRF symbol.

Structure only at bootstrap — no commands defined yet.
"""
