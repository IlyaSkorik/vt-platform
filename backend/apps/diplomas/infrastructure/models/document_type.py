"""``DocumentTypeChoices`` — the persistence mirror of the domain ``DocumentType``.

One class, used by every column that names a kind — ``TemplateModel.type``,
``AssignmentModel.document_type``, ``DiplomaModel.document_type`` and
``IssuedDocumentModel.document_type`` — so they cannot drift apart. Mirrors
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
    INDIVIDUAL_DIPLOMA = "INDIVIDUAL_DIPLOMA", "Индивидуальный диплом"
    THANK_YOU = "THANK_YOU", "Благодарность"
