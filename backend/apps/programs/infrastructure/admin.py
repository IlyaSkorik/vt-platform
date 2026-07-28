"""Django admin bindings for the Programs bounded context (read-oriented).

Support and operations only: a program is built through the organizer API, which is
where the invariants live. The admin exists so an operator can see what a public link
resolves to without a database console.
"""

from __future__ import annotations

from django.contrib import admin

from apps.programs.infrastructure.models import ProgramItemModel, ProgramModel, ProgramShareModel

__all__ = ["ProgramAdmin", "ProgramItemInline", "ProgramShareAdmin"]


class ProgramItemInline(admin.TabularInline):  # type: ignore[type-arg]
    """The running order, in order."""

    model = ProgramItemModel
    extra = 0
    fields = ("position", "number", "kind", "title", "duration_seconds", "submission_id", "deleted_at")
    readonly_fields = fields
    ordering = ("position",)

    def has_add_permission(self, request: object, obj: object = None) -> bool:
        return False


@admin.register(ProgramModel)
class ProgramAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Programs, with their items inline."""

    list_display = ("name", "competition_id", "nomination_id", "starts_at", "buffer_seconds", "updated_at")
    list_filter = ("competition_id",)
    search_fields = ("name",)
    ordering = ("-updated_at",)
    inlines = (ProgramItemInline,)


@admin.register(ProgramShareModel)
class ProgramShareAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Public editions and the slugs they answer to."""

    list_display = ("name", "slug", "program", "created_at", "deleted_at")
    search_fields = ("name", "slug")
    ordering = ("-created_at",)
