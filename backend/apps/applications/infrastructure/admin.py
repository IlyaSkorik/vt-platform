"""Django admin registrations for the Applications bounded context.

Operational surface only - no business logic. Each model is registered with its
audit timestamps made read-only.
"""

from __future__ import annotations

from django.contrib import admin

from apps.applications.infrastructure.models import ApplicationModel, ApplicationRevisionModel, SubmissionModel


class _ReadOnlyTimestampsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Base admin exposing the audit timestamps as read-only.

    (``admin.ModelAdmin`` is not subscriptable at runtime in this Django version, so
    the django-stubs generic parameter is elided with a typed ignore.)
    """

    readonly_fields = ("created_at", "updated_at", "deleted_at")


admin.site.register([SubmissionModel, ApplicationModel, ApplicationRevisionModel], _ReadOnlyTimestampsAdmin)
