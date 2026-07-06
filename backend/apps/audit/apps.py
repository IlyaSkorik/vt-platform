"""Django AppConfig for the Audit bounded context."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """App configuration for the Audit bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit"
