"""Shared orchestration helpers for the Applications command use cases.

Thin, framework-free helpers that keep every handler's body focused on its one
business operation: loading the aggregate, and enforcing the cross-context
preconditions the *application* owns (ownership and organizer authorization). The
business invariants themselves stay in the domain; these helpers only decide the
application-level questions the domain cannot see (who is acting, does the
referenced thing exist).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from apps.applications.application.exceptions import (
    ApplicationError,
    CompetitionClosedError,
    PermissionDeniedError,
    SubmissionNotFoundError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    CompetitionCatalog,
    OrganizationReadModel,
    SubmissionRepository,
)
from apps.applications.domain.entities import Application, Submission
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    ApplicationStatus,
    CompetitionId,
    NominationId,
    ReviewerId,
    SubmissionId,
    SubmissionStatus,
    UserId,
)

__all__ = [
    "ensure_editing_unlocked",
    "ensure_nomination_reachable",
    "ensure_order_editable",
    "ensure_owner",
    "ensure_reviewer",
    "ensure_submission_editable",
    "load_submission",
    "parse_reviewer_id",
    "parse_submission_id",
    "parse_user_id",
    "submission_editable_now",
    "try_resubmit_after_correction_edit",
]


def parse_submission_id(raw: str) -> SubmissionId:
    """Parse a ``SubmissionId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return SubmissionId.from_string(raw)


def parse_user_id(raw: str) -> UserId:
    """Parse a ``UserId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return UserId.from_string(raw)


def parse_reviewer_id(raw: str) -> ReviewerId:
    """Parse a ``ReviewerId`` from the command, translating validation errors."""
    with translate_domain_errors():
        return ReviewerId.from_string(raw)


def load_submission(repository: SubmissionRepository, submission_id: SubmissionId) -> Submission:
    """Load the submission or raise :class:`SubmissionNotFoundError`."""
    submission = repository.get(submission_id)
    if submission is None:
        raise SubmissionNotFoundError("Выступление не найдено — возможно, оно было удалено.")
    return submission


def ensure_owner(submission: Submission, actor: UserId) -> None:
    """Assert ``actor`` owns ``submission`` (the applicant), else deny."""
    if submission.applicant_id != actor:
        raise PermissionDeniedError("Это выступление принадлежит другому заявителю.")


def ensure_nomination_reachable(
    *,
    catalog: CompetitionCatalog,
    competition_id: CompetitionId,
    nomination_id: NominationId | None = None,
    now: datetime,
    message: str = "Регистрация закрыта: редактирование заявки недоступно.",
) -> None:
    """Assert the applicant may still get in at ``now``, else refuse.

    Two doors lead into a nomination and this helper opens either: registration while
    it is on, and the waitlist once it is off. A nomination with neither is the only
    case left to refuse, and the message says "закрыто" because from the applicant's
    side that is what happened — which door they would have used is the platform's
    business, not theirs.

    Without a ``nomination_id`` the question is the festival-wide one every step
    before the genre is picked has to ask: is there anywhere to get in at all? A
    festival whose genres have all closed but one, which keeps a list, must still let
    an applicant start — otherwise the waitlist is unreachable by the very people it
    exists for.
    """
    if catalog.accepts_submissions(competition_id=competition_id, nomination_id=nomination_id, now=now):
        return
    if catalog.accepts_waitlist(competition_id=competition_id, nomination_id=nomination_id, now=now):
        return
    raise CompetitionClosedError(message)


#: The statuses in which the entry is still an entry *being made*: a draft nobody has
#: seen yet, and a queued one that has not got in anywhere. For these two the question
#: is the entry question — "is there still a door open for me?" — and the waitlist is
#: one of the doors. Everything past them is an entry already *in* the festival, and
#: for those the only door that counts is registration itself.
_ENTRY_STILL_BEING_MADE: Final = frozenset({SubmissionStatus.DRAFT, SubmissionStatus.WAITLISTED})

#: Said to an applicant whose entry is already in the festival and whose festival has
#: stopped taking entries. Deliberately not "регистрация закрыта" alone: they are not
#: registering, they are correcting something they already sent, and the sentence has
#: to say that this is what is now over.
_EDITING_CLOSED: Final = "Приём заявок закрыт — заявку больше нельзя редактировать. Напишите организатору."

#: Said when the organizer threw the festival-wide switch. Deliberately not the
#: sentence above: the applicant may well be looking at an upload window that is still
#: days away, and "приём закрыт" would read as a mistake. Somebody decided this.
_EDITING_LOCKED: Final = "Организатор закрыл редактирование заявок — изменить ничего нельзя, включая файлы. Напишите организатору."


def submission_editable_now(
    *,
    catalog: CompetitionCatalog,
    submission: Submission,
    now: datetime,
    nomination_id: NominationId | None = None,
) -> bool:
    """Whether the *applicant* may change this entry at ``now``.

    The rule itself; :func:`ensure_submission_editable` is it with a refusal
    attached, and the read models answer with it so the screens stop offering
    what the API would refuse. Keeping the two as one function is the point: the
    button and the endpoint disagreeing is how an applicant ends up pressing
    «Сохранить» into a 409.
    """
    target = nomination_id
    if target is None and submission.performance is not None:
        target = submission.performance.nomination_id
    # The aggregate's own question first — is there still an entry to change at all.
    # A performed or cancelled number is closed to everybody, calendar or no.
    if not submission.is_editable():
        return False
    # Then the organizer's switch, before any calendar rule: the freeze is the one
    # thing that outranks «организатор вернул на доработку» below, because it is
    # thrown precisely when the organizer has stopped wanting corrections at all.
    if catalog.is_editing_locked(competition_id=submission.competition_id):
        return False
    if submission.status is SubmissionStatus.REQUIRES_CORRECTION:
        return True
    if submission.status in _ENTRY_STILL_BEING_MADE:
        return catalog.accepts_submissions(competition_id=submission.competition_id, nomination_id=target, now=now) or catalog.accepts_waitlist(
            competition_id=submission.competition_id, nomination_id=target, now=now
        )
    return catalog.accepts_submissions(competition_id=submission.competition_id, nomination_id=target, now=now)


def _locked_or_closed(catalog: CompetitionCatalog, competition_id: CompetitionId) -> str:
    """Which of the two refusals this is — a frozen festival, or one past its dates."""
    return _EDITING_LOCKED if catalog.is_editing_locked(competition_id=competition_id) else _EDITING_CLOSED


def ensure_editing_unlocked(*, catalog: CompetitionCatalog, competition_id: CompetitionId) -> None:
    """Assert the organizer has not frozen the festival, else refuse.

    The file paths need this on its own. They deliberately do not ask
    :func:`ensure_submission_editable` — a track may be replaced long after the
    applicant stopped being able to touch anything else, which is the whole reason
    the upload deadlines outlive the application one — so without this the one switch
    that is supposed to close *everything* would leave the uploads open.
    """
    if catalog.is_editing_locked(competition_id=competition_id):
        raise CompetitionClosedError(_EDITING_LOCKED)


def ensure_submission_editable(
    *,
    catalog: CompetitionCatalog,
    submission: Submission,
    now: datetime,
    nomination_id: NominationId | None = None,
) -> None:
    """Assert the *applicant* may change this entry at ``now``, else refuse.

    The aggregate decides whether there is still an entry to change; this decides
    whether its owner may be the one changing it today, which is a calendar question
    — and the calendar closes:

    * **Registration is on** for the nomination the edit concerns: edit away.
    * **The entry is still being made** — a draft, or one queued on a waitlist: the
      waitlist counts as an open door, exactly as it does on the way in. A queued
      entry waits for weeks and the act it describes goes on being rehearsed.
    * **The organizer asked for corrections**: they asked after the close as often as
      before it, and refusing the fix they requested is nobody's rule.
    * Otherwise the entry is in the festival and the festival has stopped taking
      entries — the applicant's own door is shut, and what is left is the organizer's
      correction path (``organizer_edit``), which skips this check on purpose.

    ``nomination_id`` names the nomination the edit concerns when it is not the one
    already on the entry — a performance being moved to another genre is judged by
    where it is going, not by where it has been.
    """
    # Whether there is still an entry to change at all is the aggregate's question,
    # and it answers it better: «заявка завершена или отменена» is what happened to a
    # number that has already been performed — not "приём закрыт", which would send
    # the applicant to argue about dates with an organizer who cannot help.
    if not submission.is_editable():
        return
    if submission_editable_now(catalog=catalog, submission=submission, now=now, nomination_id=nomination_id):
        return
    raise CompetitionClosedError(_locked_or_closed(catalog, submission.competition_id))


def ensure_order_editable(*, catalog: CompetitionCatalog, application: Application, now: datetime) -> None:
    """Assert the applicant may change the *order* — its performances, services, payer.

    The order's counterpart to :func:`ensure_submission_editable`, and the same split:
    a ``DRAFT`` order is being assembled, so the waitlist counts as a door; a placed
    one is in the festival, and once registration is over its composition is settled.
    The question is festival-wide because the things it guards are — a service, a
    payer and a consent belong to the order, not to any one genre.
    """
    if application.status is ApplicationStatus.DRAFT:
        ensure_nomination_reachable(catalog=catalog, competition_id=application.competition_id, now=now)
        return
    if catalog.accepts_submissions(competition_id=application.competition_id, now=now):
        return
    raise CompetitionClosedError(_locked_or_closed(catalog, application.competition_id))


def ensure_reviewer(organization: OrganizationReadModel, reviewer_id: ReviewerId) -> None:
    """Assert ``reviewer_id`` is authorized to act as an organizer, else deny."""
    if not organization.can_review_submissions(reviewer_id=reviewer_id):
        raise PermissionDeniedError("Нет прав на рассмотрение заявок.")


def try_resubmit_after_correction_edit(*, submission: Submission, catalog: CompetitionCatalog, now: datetime) -> list[DomainEvent]:
    """Auto-resubmit a corrected submission back to SUBMITTED when valid.

    Used after applicant edits while the submission is in REQUIRES_CORRECTION.
    If validation is still incomplete, keep the status unchanged and continue.
    """
    if submission.status is not SubmissionStatus.REQUIRES_CORRECTION:
        return []
    performance = submission.performance
    if performance is None:
        return []
    policy = catalog.participation_policy(
        competition_id=submission.competition_id,
        nomination_id=performance.nomination_id,
        discipline_id=performance.discipline_id,
        age_category_id=performance.age_category_id,
        participant_group_id=performance.participant_group_id,
        participation_format_id=performance.participation_format_id,
    )
    if policy is None:
        return []
    try:
        with translate_domain_errors():
            return submission.submit(policy=policy, now=now)
    except ApplicationError:
        return []
