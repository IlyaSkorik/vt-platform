"""Django admin registrations for the Judging bounded context.

Read-only on purpose. These tables hold a jury's decisions, and an admin form that let
somebody edit a mark by hand would be a way to change a result with no audit trail and
no aggregate rule applied. Support looks; corrections go through the API.
"""

from __future__ import annotations

from django.contrib import admin

from apps.judging.infrastructure.models import (
    JudgingSetupModel,
    JuryMemberModel,
    PerformanceScoringModel,
    ScorecardModel,
)


class _ReadOnlyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Look, do not touch."""

    def has_add_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False


@admin.register(JudgingSetupModel)
class JudgingSetupAdmin(_ReadOnlyAdmin):
    list_display = ("competition_id", "board_slug", "updated_at")
    search_fields = ("competition_id", "board_slug")


@admin.register(JuryMemberModel)
class JuryMemberAdmin(_ReadOnlyAdmin):
    list_display = ("full_name", "email", "competition_id", "status", "is_chair")
    list_filter = ("status", "is_chair")
    search_fields = ("full_name", "email", "competition_id")


@admin.register(PerformanceScoringModel)
class PerformanceScoringAdmin(_ReadOnlyAdmin):
    list_display = ("submission_id", "competition_id", "status", "opened_at", "closed_at")
    list_filter = ("status",)
    search_fields = ("submission_id", "competition_id")


@admin.register(ScorecardModel)
class ScorecardAdmin(_ReadOnlyAdmin):
    list_display = ("submission_id", "jury_member_id", "competition_id", "submitted_at")
    search_fields = ("submission_id", "jury_member_id", "competition_id")
