"""Django admin registrations for the Finance bounded context.

Operational surface only — no business logic (ARCH-001 architecture rules). The
expense book is registered read-only: it is edited from the operator's console,
where the amount goes through the aggregate that refuses a negative one. An
administrator correcting a figure straight in the table would bypass that, and
the figure they corrected is the one a profit total is computed from.
"""

from __future__ import annotations

from django.contrib import admin

from apps.finance.infrastructure.models import PlatformExpenseModel


class _PlatformExpenseAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """What the platform spent, and on what."""

    list_display = ("spent_at", "category", "purpose", "amount", "organization_id")
    list_filter = ("category",)
    search_fields = ("purpose", "note")
    readonly_fields = (
        "id",
        "amount",
        "category",
        "purpose",
        "note",
        "organization_id",
        "spent_at",
        "recorded_by",
        "created_at",
        "updated_at",
        "deleted_at",
        "version",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False


admin.site.register(PlatformExpenseModel, _PlatformExpenseAdmin)
