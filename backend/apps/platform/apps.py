"""Django AppConfig for the Platform bounded context."""

from django.apps import AppConfig


class PlatformConfig(AppConfig):
    """App configuration for the Platform bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform"
    label = "platform"
    verbose_name = "Platform"

    def ready(self) -> None:
        """Register the ORM models, which live in the infrastructure layer.

        Models are deliberately not in the default ``<app>/models.py`` but under
        ``infrastructure/`` (ARCH-001 §7.2, §14), so Django's automatic discovery
        does not find them — import them here to register them with the registry.
        """
        from apps.platform.infrastructure import models  # noqa: F401
