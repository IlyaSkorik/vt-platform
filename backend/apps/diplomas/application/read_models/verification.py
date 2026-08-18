"""The public diploma verification read model.

Backs the authenticity page a printed diploma's QR code points at
(``/verify/{verificationToken}`` on the web client, served by
``GET /api/v1/public/diplomas/verify/{verification_token}``). Read-only by
design: this is a projection, not a use case — it creates nothing, numbers
nothing, renders nothing and mutates nothing.

The **snapshot** is the only source of the printed facts. A diploma froze its
data at creation, so the verification page shows exactly what the paper shows —
and no other bounded context is consulted, not even to "enrich" a name. That is
what makes the page trustworthy: it cannot drift from the document in the
holder's hands.

Layering: pure and framework-free. It defines the flat view DTO the presentation
edge serializes, the read-service **port** the composition root wires to a
concrete adapter, and the pure projection rules — so those rules are unit tested
without a database.

Two fields are deliberately nullable rather than defaulted to a placeholder:

* ``degree`` — ``None`` while the jury has not sat. The page renders "результаты
  фестиваля ещё не опубликованы", which is the truth; "не указано" would suggest
  missing data instead of a pending process.
* ``official_pdf_url`` — ``None`` until the post-ceremony PDF exists. The page
  then simply has no download button, and grows one the moment the file appears
  (nothing else has to change).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from apps.diplomas.domain.value_objects import DiplomaSnapshot

__all__ = [
    "DiplomaVerificationReadService",
    "DiplomaVerificationView",
    "project_verification",
]

#: The axes, in the canonical order they are printed in, joined into the single line
#: the page shows under «Жанр». Mirrors the diploma's own block (see
#: ``infrastructure.pdf.field_values``) so page and paper agree. The first part is the
#: genre and the second the nomination — the code keeps the older identifiers
#: (``title``/``discipline``); only the displayed words changed.
_NOMINATION_PARTS = ("title", "discipline", "participant_group", "age_category")


def _clean(value: Any) -> str | None:
    """Trim to a non-empty string, or ``None``. Blank snapshot values read as absent."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class DiplomaVerificationView:
    """One diploma as shown on its public authenticity page.

    Flat and already-resolved: every value comes from the diploma's own frozen
    snapshot (plus its number, issue date and stored PDF reference), so the
    presentation edge needs no further lookups.

    ``verified`` is ``True`` for every view that exists at all — a diploma the
    read service resolved *is* an authentic, registered diploma. An unknown token
    yields no view (a 404 at the edge), never ``verified: false``.
    """

    number: str
    participant_name: str | None
    #: The person an individual diploma names, inside the collective above. ``None`` on
    #: a diploma that belongs to the performance itself — which is what tells the page
    #: whether it is verifying an ensemble's diploma or one child's.
    member_name: str | None
    competition_title: str | None
    competition_date: str | None
    nomination: str | None
    performance: str | None
    teacher: str | None
    organization: str | None
    degree: str | None
    issue_date: datetime | None
    official_pdf_url: str | None
    verified: bool = True


@runtime_checkable
class DiplomaVerificationReadService(Protocol):
    """Port the public verification edge reads through.

    One lookup, by the diploma's own ``verification_token``. Implementations must
    resolve **only** live diplomas and must not touch another bounded context.
    """

    def get_by_token(self, verification_token: str) -> DiplomaVerificationView | None:
        """The verification view for this token, or ``None`` if no diploma has it."""
        ...


def _teachers(snapshot: DiplomaSnapshot) -> str | None:
    """The teachers as one line: their names, in snapshot order, comma-separated.

    Roles are dropped — the page already labels the row "Педагог", so repeating
    "Педагог: …" inside the value would read as a stutter.
    """
    names = [name for teacher in snapshot.teachers if (name := _clean(teacher.name)) is not None]
    return ", ".join(names) or None


def _nomination(snapshot: DiplomaSnapshot) -> str | None:
    """The nomination's axes joined in canonical order, skipping the absent ones."""
    values = [value for part in _NOMINATION_PARTS if (value := _clean(getattr(snapshot.nomination, part))) is not None]
    return ", ".join(values) or None


def project_verification(
    *,
    number: str,
    snapshot: DiplomaSnapshot,
    issued_at: datetime | None,
    official_pdf_path: str | None,
) -> DiplomaVerificationView:
    """Project a diploma's frozen data into its public verification view.

    Pure: no I/O, no clock, no cross-context read. ``official_pdf_path`` is the
    stored ``/media/…`` reference (or ``None``/blank while unrendered), which the
    web client resolves against the API origin like every other stored file.
    """
    return DiplomaVerificationView(
        number=number,
        participant_name=_clean(snapshot.participant.display_name),
        member_name=_clean(snapshot.member.full_name) if snapshot.member is not None else None,
        competition_title=_clean(snapshot.competition.title),
        competition_date=_clean(snapshot.competition.date),
        nomination=_nomination(snapshot),
        performance=_clean(snapshot.performance.title),
        teacher=_teachers(snapshot),
        organization=_clean(snapshot.organization.name),
        degree=_clean(snapshot.award.degree),
        issue_date=issued_at,
        official_pdf_url=_clean(official_pdf_path),
        verified=True,
    )
