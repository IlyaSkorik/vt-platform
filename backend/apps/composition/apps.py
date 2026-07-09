"""Django AppConfig for the composition edge."""

from django.apps import AppConfig


class CompositionConfig(AppConfig):
    """App configuration for the composition edge (no models — presentation only)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.composition"
    label = "composition"
    verbose_name = "Composition edge"
