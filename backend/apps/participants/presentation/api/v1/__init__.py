"""Version 1 of the Participants REST API (API-000 §2, URI versioning).

Purpose
    The v1 contract for this context. Resource packages defined here are mounted
    under ``/api/v1/`` by ``config/urls.py`` and populated when the context's API
    contract is ratified (API-001+).

Layer responsibility
    Transport/adapter concerns only — serializers, views, URL wiring, and
    permissions. Views orchestrate application use cases and translate errors to
    RFC 9457 Problem Details; they hold no business rules.

Dependency rules
    May import Django/DRF and this context's ``application`` layer plus ``domain``
    value types. Must not be imported by any inner layer.

Structure only at bootstrap — no endpoints defined yet.
"""
