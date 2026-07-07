"""Versioned REST API surface for Participants (API-000 §2).

Purpose
    Root of this context's HTTP edge, organised by API version. Resource packages
    live under version subpackages (:mod:`.v1`) and are mounted by
    ``config/urls.py`` under ``/api/v1/`` as the contract is ratified.

Layer responsibility
    Transport/adapter concerns only — routing, serialization, and mapping domain/
    application errors to RFC 9457 Problem Details (ARCH-001 §7.6). No business
    rules; views delegate to application use cases.

Dependency rules
    May import Django/DRF and this context's ``application`` layer (use cases,
    DTOs, ports) plus ``domain`` value types. The inner layers never import this
    one — the dependency arrow points inward.

Structure only at bootstrap — no API surface defined yet.
"""
