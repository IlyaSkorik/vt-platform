"""Django AppConfig for the Notifications bounded context."""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """App configuration for the Notifications bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notifications"
