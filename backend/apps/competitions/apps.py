"""Django AppConfig for the Competitions bounded context."""

from django.apps import AppConfig


class CompetitionsConfig(AppConfig):
    """App configuration for the Competitions bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.competitions"
    label = "competitions"
    verbose_name = "Competitions"
