"""Correcting a submitted performance's content on the applicant's behalf (organizer).

One use case, not seven. What the organizer is looking at is the entry as a whole —
the number, who performs it, who prepared them — and the correction they want to make
is "let it read like this", not a sequence of add/remove instructions. So the command
carries the desired state of each section and this handler works out the difference,
which is also the only place that can report *what moved* for the letter the applicant
receives.

Three rules the applicant's own edit paths have and this one deliberately does not:

* **No registration-deadline check.** Correcting an entry after the deadline is the
  entire point — that is when the organizer is reading it.
* **No auto-resubmit.** An applicant's edit to a returned entry puts it back in the
  queue; an organizer's correction leaves the status exactly where they put it, because
  they are the one moving it.
* **No re-pricing.** The price snapshot is what the applicant was quoted and paid
  against. A correction to the entry is not a re-quote, and silently re-billing someone
  for a surname the organizer fixed would be worse than the typo.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from apps.applications.application.dto import OrganizerEditResultDto, SubmissionContentChange
from apps.applications.application.dto.commands import (
    EditSubmissionContentByOrganizerCommand,
    OrganizerParticipantInput,
    OrganizerPerformanceInput,
    OrganizerTeacherInput,
)
from apps.applications.application.exceptions import (
    InvalidInputError,
    SubmissionStateConflictError,
    translate_domain_errors,
)
from apps.applications.application.interfaces import (
    Clock,
    EventPublisher,
    OrganizationReadModel,
    SubmissionRepository,
    UuidGenerator,
)
from apps.applications.domain.entities import Participant, Submission, Teacher
from apps.applications.domain.events import DomainEvent
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    BirthDate,
    DisciplineId,
    Duration,
    Gender,
    NominationId,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    TeacherId,
    TeacherRole,
)

from ._support import ensure_reviewer, load_submission, parse_reviewer_id, parse_submission_id

__all__ = ["EditSubmissionContentByOrganizerHandler"]


def _person_or_none(*, first_name: str | None, last_name: str | None, middle_name: str | None) -> PersonName | None:
    """The structured name, or ``None`` for a collective, which has no person's name."""
    if not (first_name or "").strip() or not (last_name or "").strip():
        return None
    with translate_domain_errors():
        return PersonName(first_name=str(first_name), last_name=str(last_name), middle_name=middle_name)


def _birth_date_or_none(raw: str | None) -> BirthDate | None:
    if not (raw or "").strip():
        return None
    try:
        parsed = date.fromisoformat(str(raw))
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("Проверьте дату рождения: неверный формат.") from exc
    with translate_domain_errors():
        return BirthDate(parsed)


def _gender_or_none(raw: str | None) -> Gender | None:
    if not (raw or "").strip():
        return None
    try:
        return Gender(str(raw))
    except ValueError as exc:
        raise InvalidInputError("Укажите пол участника.") from exc


def _display_name_for(*, display_name: str | None, name: PersonName | None) -> str:
    """The caption this entry will carry.

    Derived from the name parts whenever there are any, so that correcting a surname
    also corrects the caption printed beside it. A collective has no name parts and
    supplies its own caption.
    """
    if name is not None:
        return name.full_name
    caption = (display_name or "").strip()
    if not caption:
        raise InvalidInputError("Укажите фамилию и имя участника или название коллектива.")
    return caption


def _roster(members: Sequence[str]) -> tuple[str, ...]:
    """The submitted roster with blank rows dropped — the domain normalizes the rest."""
    return tuple(cleaned for raw in members if (cleaned := " ".join(str(raw).split())))


def _stored_birth_date(participant: Participant) -> str | None:
    birth_date = participant.birth_date
    return birth_date.value.isoformat() if birth_date is not None else None


def _stored_gender(participant: Participant) -> str | None:
    gender = participant.gender
    return gender.value if gender is not None else None


class EditSubmissionContentByOrganizerHandler:
    """Use case: rewrite a live submission's content as the organizer wants it to read."""

    def __init__(
        self,
        *,
        submissions: SubmissionRepository,
        organization: OrganizationReadModel,
        clock: Clock,
        uuids: UuidGenerator,
        events: EventPublisher,
    ) -> None:
        self._submissions = submissions
        self._organization = organization
        self._clock = clock
        self._uuids = uuids
        self._events = events

    def handle(self, command: EditSubmissionContentByOrganizerCommand) -> OrganizerEditResultDto:
        now = self._clock.utcnow()
        submission = load_submission(self._submissions, parse_submission_id(command.submission_id))
        ensure_reviewer(self._organization, parse_reviewer_id(command.reviewer_id))
        if not submission.is_correctable_by_organizer():
            raise SubmissionStateConflictError(
                "Заявка завершена или отменена — изменить её нельзя.",
                domain_code="SubmissionNotEditableError",
            )

        changes: list[SubmissionContentChange] = []
        events: list[DomainEvent] = []
        if command.performance is not None:
            events += self._apply_performance(submission, command.performance, now=now, changes=changes)
        if command.participants is not None:
            events += self._apply_participants(submission, command.participants, now=now, changes=changes)
        if command.teachers is not None:
            events += self._apply_teachers(submission, command.teachers, now=now, changes=changes)

        # Nothing moved: an editor opened and saved. Saving anyway would bump the
        # version and tell the applicant their entry was corrected in no way at all.
        if not changes:
            return OrganizerEditResultDto.of(submission, (), ())

        self._submissions.save(submission)
        self._events.publish(events)
        return OrganizerEditResultDto.of(submission, tuple(changes), tuple(events))

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def _apply_performance(
        self,
        submission: Submission,
        desired: OrganizerPerformanceInput,
        *,
        now: datetime,
        changes: list[SubmissionContentChange],
    ) -> list[DomainEvent]:
        with translate_domain_errors():
            performance = Performance(
                title=PerformanceTitle(desired.title),
                duration=Duration.of_seconds(desired.duration_seconds),
                nomination_id=NominationId.from_string(desired.nomination_id),
                discipline_id=DisciplineId.from_string(desired.discipline_id),
                age_category_id=AgeCategoryId.from_string(desired.age_category_id),
                participant_group_id=ParticipantGroupId.from_string(desired.participant_group_id),
                participation_format_id=ParticipationFormatId.from_string(desired.participation_format_id),
                comment=desired.comment,
                age_composition=desired.age_composition,
            )
        current = submission.performance
        if current == performance:
            return []
        if current is not None:
            for field, before, after in (
                ("title", current.title.value, performance.title.value),
                ("duration", str(current.duration.seconds), str(performance.duration.seconds)),
                ("nomination", current.nomination_id.json(), performance.nomination_id.json()),
                ("discipline", current.discipline_id.json(), performance.discipline_id.json()),
                ("age_category", current.age_category_id.json(), performance.age_category_id.json()),
                ("participant_group", current.participant_group_id.json(), performance.participant_group_id.json()),
                ("participation_format", current.participation_format_id.json(), performance.participation_format_id.json()),
                ("comment", current.comment, performance.comment),
                ("age_composition", current.age_composition, performance.age_composition),
            ):
                if before != after:
                    changes.append(SubmissionContentChange(field=field, before=before, after=after))
        else:
            changes.append(SubmissionContentChange(field="title", before=None, after=performance.title.value))
        with translate_domain_errors():
            return submission.set_performance(performance=performance, now=now, by_organizer=True)

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def _apply_participants(
        self,
        submission: Submission,
        desired: Sequence[OrganizerParticipantInput],
        *,
        now: datetime,
        changes: list[SubmissionContentChange],
    ) -> list[DomainEvent]:
        current = {participant.id.json(): participant for participant in submission.participants}
        events: list[DomainEvent] = []

        kept: dict[str, OrganizerParticipantInput] = {}
        replaced: list[tuple[Participant, OrganizerParticipantInput]] = []
        added: list[OrganizerParticipantInput] = []
        for entry in desired:
            existing = current.get(entry.id or "")
            if existing is None:
                added.append(entry)
                continue
            if self._participant_identity_changed(existing, entry, changes=changes):
                replaced.append((existing, entry))
            else:
                kept[existing.id.json()] = entry

        addressed = {existing.id.json() for existing, _ in replaced} | set(kept)
        dropped = [participant for key, participant in current.items() if key not in addressed]

        # Removed before added: a correction regularly swaps two performers' details,
        # and the duplicate rule would refuse the second one while the first still
        # carries its old identity. The aggregate tolerates being briefly empty — the
        # "at least one participant" invariant is checked when an entry is submitted.
        for participant in dropped:
            changes.append(SubmissionContentChange(field="participant_removed", before=participant.display_name, after=None))
            with translate_domain_errors():
                events += submission.remove_participant(participant_id=participant.id, now=now, by_organizer=True)
        for existing, _ in replaced:
            with translate_domain_errors():
                events += submission.remove_participant(participant_id=existing.id, now=now, by_organizer=True)

        for existing, entry in replaced:
            # The headcount and roster of a replaced performer travel with the
            # replacement rather than through the setters, but they moved all the
            # same, and the applicant's letter has to say so.
            self._record_composition_changes(existing, entry, changes=changes)
            events += self._add_participant(
                submission,
                entry,
                now=now,
                registry_participant_id=existing.registry_participant_id,
            )
        for entry in added:
            name = _person_or_none(first_name=entry.first_name, last_name=entry.last_name, middle_name=entry.middle_name)
            changes.append(
                SubmissionContentChange(
                    field="participant_added",
                    before=None,
                    after=_display_name_for(display_name=entry.display_name, name=name),
                )
            )
            events += self._add_participant(submission, entry, now=now, registry_participant_id=None)

        for key, entry in kept.items():
            events += self._apply_participant_composition(submission, current[key], entry, now=now, changes=changes)
        return events

    def _participant_identity_changed(
        self,
        existing: Participant,
        entry: OrganizerParticipantInput,
        *,
        changes: list[SubmissionContentChange],
    ) -> bool:
        """Whether this entry now names a different person, recording each field that moved.

        "Different person" is what forces the replacement: the aggregate models
        performers as add/remove, so a corrected surname costs the entry its id. How
        many people a collective is, and who they are, are corrections *to* the entry
        and keep it — the roster typed against it must survive a headcount fix.
        """
        name = _person_or_none(first_name=entry.first_name, last_name=entry.last_name, middle_name=entry.middle_name)
        label = existing.display_name
        moved = False
        for field, before, after in (
            ("participant_name", existing.display_name, _display_name_for(display_name=entry.display_name, name=name)),
            ("participant_birth_date", _stored_birth_date(existing), (entry.birth_date or "").strip() or None),
            ("participant_gender", _stored_gender(existing), (entry.gender or "").strip() or None),
        ):
            if before != after:
                changes.append(SubmissionContentChange(field=field, before=before, after=after, subject=label))
                moved = True
        return moved

    def _apply_participant_composition(
        self,
        submission: Submission,
        existing: Participant,
        entry: OrganizerParticipantInput,
        *,
        now: datetime,
        changes: list[SubmissionContentChange],
    ) -> list[DomainEvent]:
        """Apply the headcount and roster of an entry that still names the same performer."""
        events: list[DomainEvent] = []
        self._record_composition_changes(existing, entry, changes=changes)
        if entry.member_count != existing.member_count:
            with translate_domain_errors():
                events += submission.set_participant_member_count(
                    participant_id=existing.id,
                    member_count=entry.member_count,
                    now=now,
                    by_organizer=True,
                )
        roster = _roster(entry.members)
        if roster != existing.members:
            with translate_domain_errors():
                events += submission.set_participant_members(
                    participant_id=existing.id,
                    members=roster,
                    now=now,
                    by_organizer=True,
                )
        return events

    @staticmethod
    def _record_composition_changes(
        existing: Participant,
        entry: OrganizerParticipantInput,
        *,
        changes: list[SubmissionContentChange],
    ) -> None:
        """Record a collective's headcount and roster moving, whichever path applies them."""
        label = existing.display_name
        if entry.member_count != existing.member_count:
            changes.append(
                SubmissionContentChange(
                    field="participant_member_count",
                    before=str(existing.member_count),
                    after=str(entry.member_count),
                    subject=label,
                )
            )
        roster = _roster(entry.members)
        if roster != existing.members:
            changes.append(
                SubmissionContentChange(
                    field="participant_members",
                    before=", ".join(existing.members) or None,
                    after=", ".join(roster) or None,
                    subject=label,
                )
            )

    def _add_participant(
        self,
        submission: Submission,
        entry: OrganizerParticipantInput,
        *,
        now: datetime,
        registry_participant_id: object | None,
    ) -> list[DomainEvent]:
        """Put one performer on the entry, roster and all.

        A replaced performer keeps its link to the applicant's Participant Registry:
        the entry carries a *snapshot* of that record, and correcting the snapshot is
        not the same as saying this is somebody else's child. The registry itself is
        left alone — the organizer is fixing this festival's paperwork, not the
        applicant's address book.
        """
        name = _person_or_none(first_name=entry.first_name, last_name=entry.last_name, middle_name=entry.middle_name)
        participant_id = ParticipantId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            events = submission.add_participant(
                participant_id=participant_id,
                name=name,
                birth_date=_birth_date_or_none(entry.birth_date),
                gender=_gender_or_none(entry.gender),
                display_name=_display_name_for(display_name=entry.display_name, name=name),
                registry_participant_id=registry_participant_id,  # type: ignore[arg-type]
                member_count=entry.member_count,
                members=_roster(entry.members),
                now=now,
                by_organizer=True,
            )
        return events

    # ------------------------------------------------------------------
    # Teachers
    # ------------------------------------------------------------------

    def _apply_teachers(
        self,
        submission: Submission,
        desired: Sequence[OrganizerTeacherInput],
        *,
        now: datetime,
        changes: list[SubmissionContentChange],
    ) -> list[DomainEvent]:
        current = {teacher.id.json(): teacher for teacher in submission.teachers}
        events: list[DomainEvent] = []

        replaced: list[tuple[Teacher, OrganizerTeacherInput]] = []
        added: list[OrganizerTeacherInput] = []
        untouched: set[str] = set()
        for entry in desired:
            existing = current.get(entry.id or "")
            if existing is None:
                added.append(entry)
                continue
            if self._teacher_changed(existing, entry, changes=changes):
                replaced.append((existing, entry))
            else:
                untouched.add(existing.id.json())

        addressed = {existing.id.json() for existing, _ in replaced} | untouched
        for key, teacher in current.items():
            if key in addressed:
                continue
            changes.append(SubmissionContentChange(field="teacher_removed", before=teacher.name.full_name, after=None))
            with translate_domain_errors():
                events += submission.remove_teacher(teacher_id=teacher.id, now=now, by_organizer=True)

        for existing, _ in replaced:
            with translate_domain_errors():
                events += submission.remove_teacher(teacher_id=existing.id, now=now, by_organizer=True)
        for existing, entry in replaced:
            events += self._add_teacher(submission, entry, now=now, directory_teacher_id=existing.directory_teacher_id)
        for entry in added:
            changes.append(
                SubmissionContentChange(
                    field="teacher_added",
                    before=None,
                    after=" ".join(filter(None, [entry.last_name, entry.first_name, entry.middle_name])).strip(),
                )
            )
            events += self._add_teacher(submission, entry, now=now, directory_teacher_id=None)
        return events

    def _teacher_changed(
        self,
        existing: Teacher,
        entry: OrganizerTeacherInput,
        *,
        changes: list[SubmissionContentChange],
    ) -> bool:
        """Whether this credit now reads differently, recording each field that moved."""
        name = _person_or_none(first_name=entry.first_name, last_name=entry.last_name, middle_name=entry.middle_name)
        if name is None:
            raise InvalidInputError("Укажите фамилию и имя педагога.")
        label = existing.name.full_name
        moved = False
        for field, before, after in (
            ("teacher_name", existing.name.full_name, name.full_name),
            ("teacher_role", existing.role.value, str(entry.role).strip()),
        ):
            if before != after:
                changes.append(SubmissionContentChange(field=field, before=before, after=after, subject=label))
                moved = True
        return moved

    def _add_teacher(
        self,
        submission: Submission,
        entry: OrganizerTeacherInput,
        *,
        now: datetime,
        directory_teacher_id: object | None,
    ) -> list[DomainEvent]:
        """Credit one mentor, keeping a replaced credit's link to the cabinet directory."""
        name = _person_or_none(first_name=entry.first_name, last_name=entry.last_name, middle_name=entry.middle_name)
        if name is None:
            raise InvalidInputError("Укажите фамилию и имя педагога.")
        teacher_id = TeacherId.from_uuid(self._uuids.new())
        with translate_domain_errors():
            return submission.add_teacher(
                teacher_id=teacher_id,
                name=name,
                role=TeacherRole(entry.role),
                directory_teacher_id=directory_teacher_id,  # type: ignore[arg-type]
                now=now,
                by_organizer=True,
            )
