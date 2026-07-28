"""Django AppConfig for the Programs bounded context.

Programs owns the **running order of the event itself**: the sequence an organizer
builds to actually run a festival day. A program is a first-class entity with its
own ordered items — not a projection of the accepted submissions — so the organizer
may reorder freely, insert service blocks (breaks, stage preparation, and later an
opening or an award ceremony), and publish any subset of it behind its own public
link (ARCH-001 §13.2, §14).

Distinct from Applications, which owns *what* was entered, and from Competitions,
which owns *how the competition is configured*. This context references both by id
only and never reaches into their aggregates.
"""

from __future__ import annotations

from django.apps import AppConfig


class ProgramsConfig(AppConfig):
    """App configuration for the Programs bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.programs"
    label = "programs"
    verbose_name = "Programs"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them - import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.programs.infrastructure import admin, models  # noqa: F401
