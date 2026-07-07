"""Domain events emitted by the Participants bounded context.

Purpose
    Past-tense **business facts** — the integration currency between bounded
    contexts (ARCH-001 §4.8, DATA-003). An event names something that already
    happened to a Participants aggregate (e.g. a participant registered, a
    guardian relationship verified, a participant activated), timestamps it, and
    carries just enough business data for a consumer to react without reaching
    back into this context.

Layer responsibility
    The domain only *produces* facts. There are deliberately **no** handlers,
    subscribers, dispatchers, buses, or transport here — publishing an event
    (assigning it a topic or an outbox row) is an outer-layer concern
    (``application`` / ``infrastructure``). Events are immutable, self-describing,
    and value-comparable.

Dependency rules
    Standard library only — no Django, DRF, ORM, message bus, or Celery/Kafka.
    May import :mod:`value_objects`; must not import ``application``,
    ``infrastructure``, or ``presentation``.

Structure only at bootstrap — no events defined yet.
"""
