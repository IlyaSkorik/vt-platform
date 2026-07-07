"""Database migrations for the Participants bounded context.

Purpose
    Home of this context's schema migrations. Migrations live under the
    infrastructure layer, not the default ``<app>/migrations/`` (ARCH-001 §7.2,
    §9.2, §14), so all persistence concerns sit together; the location is wired
    through ``MIGRATION_MODULES`` in settings once this context owns models.

Layer responsibility
    Persistence/schema evolution only — no business logic. Each context owns its
    own migration history and maps to its own PostgreSQL schema.

Dependency rules
    Generated against this context's ORM models; must not import ``domain``,
    ``application``, or ``presentation`` code.

Structure only at bootstrap — no migrations defined yet.
"""
