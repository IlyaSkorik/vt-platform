"""Django AppConfig for the Participants bounded context.

Purpose
    Register the Participants context with Django's app registry and pin its
    identity (``label`` ``participants``), which also names the context's
    dedicated PostgreSQL schema (ARCH-001 §9.2, §14).

Layer responsibility
    Composition/bootstrap only. This module is Django-facing glue; it holds no
    business rules. The framework-free domain and the application use cases are
    reached only through the layers below and know nothing about this config.

Dependency rules
    May import Django. Imports the context's own infrastructure adapters inside
    :meth:`ParticipantsConfig.ready` (never at module top level) so the app
    registry is fully populated first. Never imported by the domain or
    application layers.
"""

from django.apps import AppConfig


class ParticipantsConfig(AppConfig):
    """App configuration for the Participants bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.participants"
    label = "participants"
    verbose_name = "Participants"

    def ready(self) -> None:
        """Register the ORM models and admin, which live in the infrastructure layer.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings. The
        packages are empty at bootstrap; the import is the wiring that lets them
        populate later without touching this config.
        """
        from apps.participants.infrastructure import admin, models  # noqa: F401
