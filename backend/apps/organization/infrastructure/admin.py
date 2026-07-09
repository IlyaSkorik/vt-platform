"""Django admin registrations for the Organization bounded context.

Operational surface only — no business logic (ARCH-001 architecture rules). Every
model is registered with its audit timestamps made read-only; nothing else is
configured here.
"""

from __future__ import annotations

from django.contrib import admin

from apps.organization.infrastructure.models import (
    OrganizationModel,
    StaffInvitationModel,
    StaffMembershipModel,
)


class _ReadOnlyTimestampsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Base admin exposing the audit timestamps as read-only.

    Timestamps are written by the domain/mapper and are never editable in admin.
    (``admin.ModelAdmin`` is not subscriptable at runtime in this Django version,
    so the django-stubs generic parameter is elided with a typed ignore.)
    """

    readonly_fields = ("created_at", "updated_at", "deleted_at")


admin.site.register(
    [
        OrganizationModel,
        StaffMembershipModel,
        StaffInvitationModel,
    ],
    _ReadOnlyTimestampsAdmin,
)
