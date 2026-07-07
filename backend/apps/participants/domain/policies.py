"""Business policies for the Participants bounded context.

Purpose
    Explicit, testable **business rules** expressed as immutable, injectable
    policies (ARCH-001 §4.2, §13.4). Candidate policies for this context include
    guardian-relationship verification, consent requirements for acting on a
    minor's behalf, age-group derivation and eligibility, and institution/teacher
    authorisation (DATA-001 §3.4, §4.2; DATA-002). Extracting rules into policies
    keeps the Open/Closed principle: behaviour extends by adding a policy rather
    than editing an aggregate.

Layer responsibility
    Each policy is configuration-as-data (a frozen, slotted dataclass whose
    fields are its knobs) and returns a rich decision — or raises a typed policy
    error — never reads global state or performs IO. Any method reasoning about
    time takes the current instant (``now``) as an argument, so decisions are
    deterministic.

Dependency rules
    Standard library only — no Django, DRF, ORM, or clock. May import
    :mod:`value_objects` and :mod:`exceptions`; must not import ``application``,
    ``infrastructure``, or ``presentation``. Policies are constructed by the
    composition root and injected into use cases (Dependency Inversion).

Structure only at bootstrap — no policies defined yet.
"""
