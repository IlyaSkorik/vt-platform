"""Django AppConfig for the Performances bounded context."""

from django.apps import AppConfig


class PerformancesConfig(AppConfig):
    """App configuration for the Performances bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.performances"
    label = "performances"
    verbose_name = "Performances"
