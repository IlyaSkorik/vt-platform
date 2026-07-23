"""Django AppConfig for the Diplomas bounded context.

Diplomas is a standalone organizer workspace (not a competition setting): it owns
the reusable diploma **template library** and the **assignment** mechanism that
binds a template to a (competition, nomination) pair. Templates are self-contained
entities — one template may be assigned across many competitions and nominations.
"""

from __future__ import annotations

from django.apps import AppConfig


class DiplomasConfig(AppConfig):
    """App configuration for the Diplomas bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.diplomas"
    label = "diplomas"
    verbose_name = "Diplomas"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them - import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.diplomas.infrastructure import admin, models  # noqa: F401
