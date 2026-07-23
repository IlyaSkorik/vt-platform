"""Django admin registrations for the Diplomas bounded context.

Operational surface only - no business logic. Each model is registered with its
audit timestamps made read-only.
"""

from __future__ import annotations

from django.contrib import admin

from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    TemplateDocumentModel,
    TemplateFieldModel,
    TemplateModel,
)


class _ReadOnlyTimestampsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Base admin exposing the audit timestamps as read-only.

    (``admin.ModelAdmin`` is not subscriptable at runtime in this Django version, so
    the django-stubs generic parameter is elided with a typed ignore.)
    """

    readonly_fields = ("created_at", "updated_at", "deleted_at")


admin.site.register(
    [TemplateModel, TemplateDocumentModel, TemplateFieldModel, AssignmentModel],
    _ReadOnlyTimestampsAdmin,
)
