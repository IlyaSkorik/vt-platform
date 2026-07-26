"""``DocumentTypeChoices`` — the persistence mirror of the domain ``DocumentType``.

One class, used by both ``TemplateModel.type`` and ``AssignmentModel.document_type``,
so the two columns cannot drift apart. Mirrors
:class:`~apps.diplomas.domain.document_types.DocumentType`; a test asserts the two
stay in step, which is what makes adding a third kind a one-line change on each
side rather than a hunt.
"""

from __future__ import annotations

from django.db import models

__all__ = ["DocumentTypeChoices"]


class DocumentTypeChoices(models.TextChoices):
    """A kind of document a template produces (mirrors the domain enum)."""

    DIPLOMA = "DIPLOMA", "Диплом"
    THANK_YOU = "THANK_YOU", "Благодарность"
