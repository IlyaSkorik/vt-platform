"""Django AppConfig for the Identity & Access bounded context."""

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    """App configuration for the Identity & Access bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
    label = "identity"
    verbose_name = "Identity & Access"
