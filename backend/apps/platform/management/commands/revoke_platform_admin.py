"""``revoke_platform_admin`` — withdraw an account's platform-operator access.

The counterpart of ``grant_platform_admin``, and equally command-only. The grant
record survives the withdrawal, so who could read across every organization, and
until when, stays answerable.

Usage::

    python manage.py revoke_platform_admin --email someone@example.com
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.identity.domain.value_objects import Email
from apps.identity.infrastructure.repositories import DjangoUserRepository
from apps.platform.application.dto import RevokePlatformAdministratorCommand
from apps.platform.application.exceptions import ApplicationError
from apps.platform.composition import build_revoke_platform_administrator_handler


class Command(BaseCommand):
    """Revoke platform-operator access from an account, by email."""

    help = "Revoke platform-administrator access from a user, by email."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", required=True, help="Email of the account whose platform access is withdrawn.")

    def handle(self, *args: Any, **options: Any) -> None:
        raw_email = str(options["email"]).strip()

        try:
            email = Email(raw_email)
        except ValueError as exc:
            raise CommandError(f"Invalid email address: {raw_email!r}.") from exc

        user = DjangoUserRepository().get_by_email(email)
        if user is None:
            raise CommandError(f"No registered user found with email {raw_email!r}.")

        try:
            build_revoke_platform_administrator_handler().handle(RevokePlatformAdministratorCommand(user_id=user.id.json()))
        except ApplicationError as exc:
            raise CommandError(f"Could not revoke platform access: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"{raw_email} no longer has platform administrator access."))
