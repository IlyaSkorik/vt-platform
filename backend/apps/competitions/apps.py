"""Django AppConfig for the Competitions bounded context."""

from django.apps import AppConfig


class CompetitionsConfig(AppConfig):
    """App configuration for the Competitions bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.competitions"
    label = "competitions"
    verbose_name = "Competitions"

    def ready(self) -> None:
        """Register the ORM models and admin, which live in the infrastructure layer.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them — import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.competitions.infrastructure import admin, models  # noqa: F401
