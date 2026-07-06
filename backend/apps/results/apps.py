"""Django AppConfig for the Results bounded context."""

from django.apps import AppConfig


class ResultsConfig(AppConfig):
    """App configuration for the Results bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.results"
    label = "results"
    verbose_name = "Results"
