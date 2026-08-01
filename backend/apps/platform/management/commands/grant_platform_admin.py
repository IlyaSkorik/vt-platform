"""``grant_platform_admin`` — give a registered account platform-operator access.

Platform access is what sits above every organization: connecting new ones,
setting what each owes the platform, and reading across all of them. There is no
endpoint that hands it out — an organization must never be able to promote anyone
to the level that governs it — so this command is the only way in.

**Composition-edge** code: the single sanctioned place allowed to know two
bounded contexts. It resolves the email to an account through Identity's own
repository, then hands the opaque user id to the Platform use case; neither
context's domain learns about the other.

Usage::

    python manage.py grant_platform_admin --email me@example.com
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.identity.domain.value_objects import Email
from apps.identity.infrastructure.repositories import DjangoUserRepository
from apps.platform.application.dto import GrantPlatformAdministratorCommand
from apps.platform.application.exceptions import ApplicationError
from apps.platform.composition import build_grant_platform_administrator_handler


class Command(BaseCommand):
    """Grant platform-operator access to an existing user account, by email."""

    help = "Grant platform-administrator access to an existing registered user, by email."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--email",
            required=True,
            help="Email of an existing, registered user to grant platform access to.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        raw_email = str(options["email"]).strip()

        try:
            email = Email(raw_email)
        except ValueError as exc:
            raise CommandError(f"Invalid email address: {raw_email!r}.") from exc

        user = DjangoUserRepository().get_by_email(email)
        if user is None:
            raise CommandError(f"No registered user found with email {raw_email!r}. The account must exist before it can be granted platform access.")

        try:
            view = build_grant_platform_administrator_handler().handle(GrantPlatformAdministratorCommand(user_id=user.id.json()))
        except ApplicationError as exc:
            raise CommandError(f"Could not grant platform access: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"{raw_email} is a platform administrator (granted at {view.granted_at.isoformat()})."))
