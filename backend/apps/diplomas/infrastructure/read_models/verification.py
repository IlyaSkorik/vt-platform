"""ORM-backed adapter for the public diploma verification read model.

One indexed lookup on ``diplomas_diploma.verification_token`` (globally unique),
then the pure :func:`project_verification`. The row's frozen ``snapshot`` column
is the whole data source — no join, no other bounded context, no aggregate
rehydration.

A soft-deleted diploma is indistinguishable from an unknown token: both read as
``None``, so a revoked document never verifies and its former existence is not
leaked either.
"""

from __future__ import annotations

from apps.diplomas.application.read_models.verification import (
    DiplomaVerificationView,
    project_verification,
)
from apps.diplomas.domain.value_objects import DiplomaSnapshot
from apps.diplomas.infrastructure.models import DiplomaModel

__all__ = ["DjangoDiplomaVerificationReader"]

#: Upper bound on an accepted token, matching ``DiplomaModel.verification_token``.
#: Anything longer cannot be a real token, so it is rejected without a query.
_MAX_TOKEN_LENGTH = 64


class DjangoDiplomaVerificationReader:
    """Concrete ``DiplomaVerificationReadService`` over the Django ORM."""

    def get_by_token(self, verification_token: str) -> DiplomaVerificationView | None:
        token = (verification_token or "").strip()
        if not token or len(token) > _MAX_TOKEN_LENGTH:
            return None
        row = (
            DiplomaModel.objects.filter(verification_token=token, deleted_at__isnull=True)
            .only("number", "snapshot", "issued_at", "official_pdf_path")
            .first()
        )
        if row is None:
            return None
        return project_verification(
            number=row.number,
            snapshot=DiplomaSnapshot.from_dict(row.snapshot or {}),
            issued_at=row.issued_at,
            official_pdf_path=row.official_pdf_path or None,
        )
