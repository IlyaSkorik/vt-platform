"""``list_platform_admins`` — show who holds (or held) platform-operator access.

Usage::

    python manage.py list_platform_admins
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.identity.infrastructure.models import UserModel
from apps.platform.composition import build_list_platform_administrators_handler


class Command(BaseCommand):
    """List every platform-administrator grant, revoked ones included."""

    help = "List platform administrators (revoked grants are shown too)."

    def handle(self, *args: Any, **options: Any) -> None:
        grants = build_list_platform_administrators_handler().handle()
        if not grants:
            self.stdout.write("No platform administrators. Grant one with: manage.py grant_platform_admin --email <email>")
            return

        emails = {str(row["id"]): str(row["email"]) for row in UserModel.objects.filter(id__in=[g.user_id for g in grants]).values("id", "email")}
        for grant in grants:
            state = "active" if grant.is_active else f"revoked {grant.revoked_at:%Y-%m-%d}"
            self.stdout.write(f"{emails.get(grant.user_id, grant.user_id)} — {state} (granted {grant.granted_at:%Y-%m-%d})")
