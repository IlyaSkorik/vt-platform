"""Django AppConfig for the Teacher Directory bounded context."""

from django.apps import AppConfig


class TeachersConfig(AppConfig):
    """App configuration for the Teacher Directory bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teachers"
    label = "teachers"
    verbose_name = "Teacher Directory"

    def ready(self) -> None:
        """Register the ORM models and admin, which live under ``infrastructure/``.

        Models and admin are deliberately not in the default ``<app>/models.py`` /
        ``<app>/admin.py`` but under ``infrastructure/`` (ARCH-001 §7.2, §14), so
        Django's automatic discovery does not find them - import them here to
        register the models with the app registry and their admin bindings.
        """
        from apps.teachers.infrastructure import admin, models  # noqa: F401
