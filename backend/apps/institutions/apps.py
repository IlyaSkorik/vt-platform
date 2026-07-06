"""Django AppConfig for the Institutions bounded context."""

from django.apps import AppConfig


class InstitutionsConfig(AppConfig):
    """App configuration for the Institutions bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.institutions"
    label = "institutions"
    verbose_name = "Institutions"
