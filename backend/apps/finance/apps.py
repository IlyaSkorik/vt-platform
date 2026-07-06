"""Django AppConfig for the Finance bounded context."""

from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """App configuration for the Finance bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = "Finance"
