"""Django admin registrations for the Notifications bounded context.

Operational surface only — no business logic (ARCH-001 architecture rules). Support
needs to answer "was this person actually told, and when did they open it", which is
a read of the feed rather than anything to edit.
"""

from __future__ import annotations

from django.contrib import admin

from apps.notifications.infrastructure.models import NotificationModel


@admin.register(NotificationModel)
class NotificationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]  # not subscriptable at runtime in this Django version
    """Read-oriented admin for the cabinet notification feed."""

    list_display = ("kind", "title", "recipient_id", "created_at", "read_at")
    list_filter = ("kind",)
    search_fields = ("title", "recipient_id")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
