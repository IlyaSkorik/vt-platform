"""Repository implementations for the Participants bounded context.

Purpose
    ORM-backed adapters that implement the ports declared in
    :mod:`apps.participants.application.interfaces` and
    :mod:`apps.participants.domain.interfaces` (ARCH-001 §7.2) — the only gateway
    between this context's aggregates and persistence.

Layer responsibility
    Translate use-case calls into ORM queries and back, delegating domain
    <-> model conversion to the mappers. Repositories hold no business rules;
    they satisfy an inner-layer contract from the outside.

Dependency rules
    May import Django ORM, this context's ORM models, and the mappers. Depends
    inward on the ``domain``/``application`` ports it implements; must not import
    ``presentation``. A package so repositories can be split per aggregate.

Structure only at bootstrap — no repositories defined yet.
"""
