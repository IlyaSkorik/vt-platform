"""Django admin registrations for the Reviews bounded context.

Operational surface only — no business logic. A note is registered read-only in
full: it is what a stranger said, and an administrator able to edit it would turn
the table into something other than a record of what was said. Removing one is
still possible, because that is the action a complaint actually calls for.
"""

from __future__ import annotations

from django.contrib import admin

from apps.reviews.infrastructure.models import ReviewModel, ReviewPageModel


class _ReviewPageAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """The page an organizer prints a code of."""

    list_display = ("title", "slug", "organization_id", "accepting", "created_at")
    search_fields = ("slug", "title")
    readonly_fields = ("id", "slug", "created_at", "updated_at", "deleted_at", "version")


class _ReviewAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """A note is a fact. Nothing here may change one."""

    list_display = ("author_name", "organization_id", "competition_title", "submitted_at")
    search_fields = ("author_name", "text")
    readonly_fields = (
        "id",
        "page",
        "organization_id",
        "author_name",
        "text",
        "photos",
        "competition_id",
        "competition_title",
        "consent_version",
        "consent_accepted_at",
        "submitted_at",
        "created_at",
        "updated_at",
        "version",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False


admin.site.register(ReviewPageModel, _ReviewPageAdmin)
admin.site.register(ReviewModel, _ReviewAdmin)
