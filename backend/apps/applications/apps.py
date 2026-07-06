"""Django AppConfig for the Applications bounded context."""

from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    """App configuration for the Applications bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.applications"
    label = "applications"
    verbose_name = "Applications"
