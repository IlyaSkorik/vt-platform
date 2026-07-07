"""Value objects for the Participants bounded context.

Purpose
    Immutable, identity-less concepts of the Participants domain (DATA-001 §8) —
    the intended set includes identifiers, personal-name shapes under data
    minimization, date of birth and the **derived** age group, relationship and
    membership status, and the pseudonymized display alias used for blind judging
    (DATA-001 §4.2). Each value object validates its own input on construction,
    is compared by value, and can never be mutated afterwards, so an invalid
    value simply cannot exist at runtime.

Layer responsibility
    Self-validating building blocks assembled by entities. They hold no
    persistence, transport, or formatting concerns beyond rendering their own
    value; outer layers depend on these types, never the reverse.

Dependency rules
    Standard library only — no Django, DRF, ORM, Pydantic, or third-party
    validators. May import :mod:`exceptions`; must not import ``application``,
    ``infrastructure``, or ``presentation``.

Structure only at bootstrap — no value objects defined yet.
"""
