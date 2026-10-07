"""Draft-lifecycle use cases: create a submission, delete a draft."""

from __future__ import annotations

from apps.applications.application.dto import SubmissionOperationResultDto
from apps.applications.application.dto.commands import (
    CreateSubmissionCommand,
    DeleteDraftSubmissionCommand,
)
from apps.applications.application.exceptions import (
    ApplicantNotFoundError,
    CompetitionNotFoundError,
    SubmissionStateConflictError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    CompetitionCatalog,
    EventPublisher,
    IdentityReadModel,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.entities import Submission
from apps.applications.domain.value_objects import CompetitionId, SubmissionId, UserId

from ._support import ensure_nomination_reachable, ensure_owner, load_submission, parse_submission_id, parse_user_id

__all__ = ["CreateSubmissionHandler", "DeleteDraftSubmissionHandler"]


class CreateSubmissionHandler:
    """Use case: create a new DRAFT submission for a competition.

    Validates the *application*-owned preconditions - the applicant exists, the
    competition exists and currently accepts submissions - then lets the domain
    factory establish the draft. The content is built up by later use cases.
    """

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        catalog: CompetitionCatalog,
        identity: IdentityReadModel,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._catalog = catalog
        self._identity = identity
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: CreateSubmissionCommand) -> SubmissionOperationResultDto:
        now = self._clock.utcnow()
        with translate_domain_errors():
            competition_id = CompetitionId.from_string(command.competition_id)
            applicant_id = UserId.from_string(command.applicant_id)

        if not self._identity.exists(user_id=applicant_id):
            raise ApplicantNotFoundError("Профиль заявителя не найден. Войдите в систему заново.")
        if not self._catalog.exists(competition_id):
            raise CompetitionNotFoundError("Фестиваль не найден.")
        ensure_nomination_reachable(
            catalog=self._catalog,
            competition_id=competition_id,
            now=now,
            message="Приём заявок на этот фестиваль закрыт.",
        )

        submission_id = SubmissionId.from_uuid(self._uuids.new())
        submission, domain_events = Submission.draft(
            submission_id=submission_id,
            competition_id=competition_id,
            applicant_id=applicant_id,
            now=now,
        )
        self._submissions.save(submission)
        self._events.publish(domain_events)
        return SubmissionOperationResultDto.of(submission, tuple(domain_events))


class DeleteDraftSubmissionHandler:
    """Use case: delete a draft submission.

    The domain exposes no delete transition (a submitted submission's history must
    be preserved), so this use case enforces the "only a DRAFT may be deleted"
    precondition against the aggregate's own predicate, then removes it through the
    repository. No domain event is produced - a never-submitted draft leaves no
    business fact behind.
    """

    def __init__(self, *, submissions: SubmissionRepository) -> None:
        self._submissions = submissions

    def handle(self, command: DeleteDraftSubmissionCommand) -> None:
        submission_id = parse_submission_id(command.submission_id)
        requested_by = parse_user_id(command.requested_by)

        submission = load_submission(self._submissions, submission_id)
        ensure_owner(submission, requested_by)
        if not submission.is_draft():
            raise SubmissionStateConflictError(
                "Удалить можно только черновик — это выступление уже подано.",
                domain_code="draft_deletion_only",
            )
        self._submissions.delete(submission_id)
