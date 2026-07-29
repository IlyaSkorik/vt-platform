"""Django admin bindings for the Results bounded context (read-only).

Support and operations only, and read-only deliberately: results are entered and published
through the organizer API, which is where the invariants live and where publication triggers
the diplomas and the mail. An award edited here would change what a protocol says without
changing the diploma that quotes it - the one inconsistency in this context that nobody
could explain to a participant. The admin exists so an operator can see what a public link
resolves to and which revision is out there, without a database console.
"""

from __future__ import annotations

from django.contrib import admin

from apps.results.infrastructure.models import ProtocolModel, ProtocolRowModel

__all__ = ["ProtocolAdmin", "ProtocolRowInline"]


class ProtocolRowInline(admin.TabularInline):  # type: ignore[type-arg]
    """The protocol, in performance order."""

    model = ProtocolRowModel
    extra = 0
    fields = ("position", "number", "submission_id", "award", "deleted_at")
    readonly_fields = fields
    ordering = ("position",)

    def has_add_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False


@admin.register(ProtocolModel)
class ProtocolAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Protocols, with their rows inline."""

    list_display = ("name", "competition_id", "nomination_id", "status", "revision", "slug", "published_at")
    list_filter = ("status", "competition_id")
    search_fields = ("name", "slug")
    ordering = ("-published_at", "-created_at")
    inlines = (ProtocolRowInline,)
    readonly_fields = (
        "id",
        "competition_id",
        "nomination_id",
        "name",
        "status",
        "public_columns",
        "slug",
        "revision",
        "published_at",
        "published_version",
        "published_snapshot",
        "seeded_from_program_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "version",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False
