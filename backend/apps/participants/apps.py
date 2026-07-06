"""Django AppConfig for the Participants bounded context."""

from django.apps import AppConfig


class ParticipantsConfig(AppConfig):
    """App configuration for the Participants bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.participants"
    label = "participants"
    verbose_name = "Participants"
