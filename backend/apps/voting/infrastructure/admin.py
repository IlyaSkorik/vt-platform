"""Django admin registrations for the Voting bounded context.

Operational surface only — no business logic. Votes are registered read-only in
full: an append-only record that an administrator could edit is not a record.
"""

from __future__ import annotations

from django.contrib import admin

from apps.voting.infrastructure.models import BallotModel, BallotNomineeModel, VoteModel


class _ReadOnlyTimestampsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Base admin exposing the audit timestamps as read-only."""

    readonly_fields = ("created_at", "updated_at", "deleted_at")


class _VoteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """A vote is a fact. Nothing here may change one."""

    readonly_fields = ("id", "ballot_id", "nominee_id", "voter_key", "network_key", "bucket", "created_at")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False


admin.site.register([BallotModel, BallotNomineeModel], _ReadOnlyTimestampsAdmin)
admin.site.register(VoteModel, _VoteAdmin)
