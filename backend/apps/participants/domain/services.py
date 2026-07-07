"""Domain services for the Participants bounded context.

Purpose
    Stateless business behaviour that does not belong to a single entity or value
    object — coordination across aggregates within this context (ARCH-001 §13.4),
    such as reasoning that spans a Participant and its Guardian/Teacher
    Relationships. Used only when a rule has no natural home on one aggregate; a
    rule that fits an entity stays on that entity.

Layer responsibility
    Pure orchestration of domain objects. Domain services hold no state, own no
    persistence, and emit their results as return values / domain events for an
    outer layer to dispatch.

Dependency rules
    Standard library only — no Django, DRF, ORM, or persistence. May import
    sibling domain modules; must not import ``application``, ``infrastructure``,
    or ``presentation``.

Structure only at bootstrap — no services defined yet.
"""
