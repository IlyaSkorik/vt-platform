"""Ports (abstract interfaces) for the Participants bounded context.

Purpose
    Repository and gateway **protocols** that the domain and application layers
    depend on to reach the outside world (persistence of the Participant and
    related aggregates, and any domain-owned gateways) without knowing the
    concrete technology. Concrete adapters are injected at composition time
    (ARCH-001 §7.3, Dependency Inversion).

Layer responsibility
    Contracts only — never implementations. Expressed as fully typed structural
    :class:`typing.Protocol` seams so an adapter can satisfy a port without
    importing or inheriting from it, keeping the core free of outward edges.

Dependency rules
    Standard library only — no Django, DRF, ORM, or IO. May reference this
    context's domain types (entities, value objects); must not import
    ``application``, ``infrastructure``, or ``presentation``. Infrastructure
    depends on this module, never the reverse.

Structure only at bootstrap — no ports defined yet.
"""
