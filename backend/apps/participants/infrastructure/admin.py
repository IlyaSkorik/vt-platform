"""Django admin registrations for the Participants bounded context.

Purpose
    Operational back-office surface for staff to inspect this context's records
    (participants, guardians, teachers, relationships). Bindings are registered
    from here because they attach to the ORM models under
    :mod:`apps.participants.infrastructure.models`, which live in this layer
    (ARCH-001 §7.2, §14).

Layer responsibility
    Adapter/operational glue only — no business logic. Any rule shown or enforced
    in admin still belongs to the domain; admin merely reads and writes through
    the models.

Dependency rules
    May import Django and this context's ORM models. Imported by
    :meth:`apps.participants.apps.ParticipantsConfig.ready` so registrations load
    once the app registry is ready. Must never be imported by ``domain`` or
    ``application``.

Structure only at bootstrap — no admin registrations defined yet.
"""
