"""Django AppConfig for the Analytics bounded context."""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """App configuration for the Analytics bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    label = "analytics"
    verbose_name = "Analytics"
