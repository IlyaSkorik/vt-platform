"""``bootstrap_owner`` — provision the first staff OWNER for an environment.

There is **no public way** to create staff: the first OWNER is created here, once
per environment, and every subsequent staff member is added only through
invitations. This command is **composition-edge** code — the single sanctioned
place allowed to know both bounded contexts: it resolves an email to a user via
Identity's repository, then hands the resulting user id to the Organization
use case. Neither context's domain/application layer learns about the other.

Usage::

    python manage.py bootstrap_owner --email owner@example.com
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.identity.domain.value_objects import Email
from apps.identity.infrastructure.repositories import DjangoUserRepository
from apps.organization.application.dto.commands import ProvisionOwnerCommand
from apps.organization.application.exceptions import ApplicationError
from apps.organization.composition import build_provision_owner_handler


class Command(BaseCommand):
    """Provision the first OWNER staff membership for an existing user account."""

    help = "Create the first staff OWNER for an existing user, by email (run once per environment)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--email",
            required=True,
            help="Email of an existing, registered user to make the first OWNER.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        raw_email = str(options["email"]).strip()

        # Resolve the email to a user through Identity's own contracts. The command
        # is the only place permitted to cross contexts; it passes the resulting
        # opaque user id onward, never an Identity type.
        try:
            email = Email(raw_email)
        except ValueError as exc:
            raise CommandError(f"Invalid email address: {raw_email!r}.") from exc

        user = DjangoUserRepository().get_by_email(email)
        if user is None:
            raise CommandError(f"No registered user found with email {raw_email!r}. The user must register (and exist) before being made an owner.")

        command = ProvisionOwnerCommand(user_id=user.id.json())
        try:
            result = build_provision_owner_handler().handle(command)
        except ApplicationError as exc:
            raise CommandError(f"Could not provision owner: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"Provisioned OWNER for {raw_email} (role={result.membership.role}, status={result.membership.status}).")
        )
