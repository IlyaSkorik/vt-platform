"""Django AppConfig for the Judging bounded context."""

from django.apps import AppConfig


class JudgingConfig(AppConfig):
    """App configuration for the Judging bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.judging"
    label = "judging"
    verbose_name = "Judging"
