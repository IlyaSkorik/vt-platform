"""The organizer's correction of a submitted entry — the applicant's data, fixed in place.

Why this exists at all. An entry is a *snapshot*: the performers on it are copies of
the applicant's registry records, frozen at the moment they were added, and the
organizer is the one who decides what the festival's paperwork says. When a surname
arrives misspelt — and it is the surname that will be printed on a diploma — the only
repair the platform offered was "вернуть на исправление": a round trip through the
applicant, who must log in, find the order, retype one letter and resubmit, while the
entry sits out of the queue. For a typo the organizer is already looking at, that is a
worse outcome for everyone than fixing it.

So the correction is made here, and everything that makes it *accountable* is made
here with it: what moved is recorded on the submission, the applicant is told in a
letter and in their feed, and the card's history shows who changed what and when. The
correction is never silent — that is the price of letting one person edit another's
entry, and it is worth paying.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from apps.applications.application.dto import SubmissionContentChange
from apps.applications.application.dto.commands import (
    EditSubmissionContentByOrganizerCommand,
    OrganizerParticipantInput,
    OrganizerPerformanceInput,
    OrganizerTeacherInput,
)
from apps.applications.application.exceptions import ApplicationError
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.mail import queue_review_email
from apps.applications.presentation.api.v1.organizer.content_serializers import OrganizerSubmissionContentSerializer
from apps.applications.presentation.api.v1.submissions import composition
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.emailing import render_transactional_email_html
from apps.identity.infrastructure.models.user import UserModel
from apps.notifications.infrastructure import feed as notification_feed
from apps.notifications.infrastructure.models import NotificationKind

from .views import (
    _application_meta_for_submission,
    _application_urls,
    _cabinet_path,
    _capabilities,
    _now,
    _StaffView,
)

#: How each changed field is named to a human. The keys are the application layer's
#: own field names — it states *what* moved, this table says it in Russian.
_FIELD_LABELS: dict[str, str] = {
    "title": "Название номера",
    "duration": "Длительность",
    "nomination": "Жанр",
    "discipline": "Номинация",
    "age_category": "Возрастная категория",
    "participant_group": "Состав",
    "participation_format": "Форма участия",
    "comment": "Комментарий к выступлению",
    "age_composition": "Возрастной состав",
    "participant_name": "Участник",
    "participant_birth_date": "Дата рождения",
    "participant_gender": "Пол",
    "participant_member_count": "Численность коллектива",
    "participant_members": "Состав коллектива",
    "participant_added": "Добавлен участник",
    "participant_removed": "Удалён участник",
    "teacher_name": "Педагог",
    "teacher_role": "Роль педагога",
    "teacher_added": "Добавлен педагог",
    "teacher_removed": "Удалён педагог",
}

#: Fields whose stored value is an id from the competition's own configuration. They
#: are the only ones that need the name maps; everything else is already text.
_TAXONOMY_FIELDS = frozenset({"nomination", "discipline", "age_category", "participant_group", "participation_format"})

#: Fields that name a thing arriving or leaving rather than a value moving, so the
#: line reads "Добавлен участник: Иванова Анна", not "… : — → Иванова Анна".
_SINGLE_VALUE_FIELDS = frozenset({"participant_added", "participant_removed", "teacher_added", "teacher_removed"})

_GENDER_LABELS = {"MALE": "мужской", "FEMALE": "женский", "OTHER": "другой"}


def _duration_label(raw: str | None) -> str:
    """Seconds as ``м:сс`` — the shape the organizer types them in."""
    try:
        total = max(0, int(str(raw)))
    except (TypeError, ValueError):
        return "—"
    return f"{total // 60}:{total % 60:02d}"


def _taxonomy_names(competition_id: str) -> dict[str, dict[str, str]]:
    """The competition's own names for the ids a correction moves between.

    Read for one competition rather than for the whole workspace: this is a single
    entry's correction, and a letter that says "Возраст: 7-9 лет → 10-12 лет" needs
    exactly the two rows involved.
    """
    competition_key = uuid.UUID(competition_id)
    return {
        "nomination": {
            str(row["id"]): str(row["name"])
            for row in CategoryModel.objects.filter(deleted_at__isnull=True, competition_id=competition_key).values("id", "name")
        },
        "discipline": {
            str(row["id"]): str(row["name"])
            for row in DisciplineModel.objects.filter(deleted_at__isnull=True, competition_id=competition_key).values("id", "name")
        },
        "age_category": {
            str(row["id"]): str(row["name"])
            for row in AgeCategoryModel.objects.filter(deleted_at__isnull=True, competition_id=competition_key).values("id", "name")
        },
        "participant_group": {
            str(row["id"]): str(row["name"])
            for row in ParticipantGroupModel.objects.filter(deleted_at__isnull=True, competition_id=competition_key).values("id", "name")
        },
        "participation_format": {
            str(row["id"]): str(row["name"])
            for row in ParticipationFormatModel.objects.filter(deleted_at__isnull=True, competition_id=competition_key).values("id", "name")
        },
    }


def _value_label(change: SubmissionContentChange, raw: str | None, names: Mapping[str, Mapping[str, str]]) -> str:
    """One side of a change, rendered the way the organizer's own screen shows it."""
    if raw is None or not str(raw).strip():
        return "—"
    value = str(raw)
    if change.field in _TAXONOMY_FIELDS:
        return names.get(change.field, {}).get(value, value)
    if change.field == "duration":
        return _duration_label(value)
    if change.field == "participant_gender":
        return _GENDER_LABELS.get(value, value)
    return value


def _change_line(change: SubmissionContentChange, names: Mapping[str, Mapping[str, str]]) -> str:
    """One correction as a sentence — the same text in the journal, the card and the letter."""
    label = _FIELD_LABELS.get(change.field, change.field)
    if change.field in _SINGLE_VALUE_FIELDS:
        return f"{label}: {_value_label(change, change.after or change.before, names)}"
    subject = f" «{change.subject}»" if change.subject else ""
    return f"{label}{subject}: {_value_label(change, change.before, names)} → {_value_label(change, change.after, names)}"


def _participant_input(entry: Mapping[str, Any]) -> OrganizerParticipantInput:
    birth_date = entry.get("birthDate")
    return OrganizerParticipantInput(
        id=(entry.get("id") or "").strip() or None,
        display_name=(entry.get("displayName") or "").strip() or None,
        first_name=(entry.get("firstName") or "").strip() or None,
        last_name=(entry.get("lastName") or "").strip() or None,
        middle_name=(entry.get("middleName") or "").strip() or None,
        birth_date=birth_date.isoformat() if birth_date else None,
        gender=(entry.get("gender") or "").strip() or None,
        member_count=int(entry.get("memberCount") or 1),
        members=tuple(str(name) for name in entry.get("members") or ()),
    )


def _teacher_input(entry: Mapping[str, Any]) -> OrganizerTeacherInput:
    return OrganizerTeacherInput(
        id=(entry.get("id") or "").strip() or None,
        first_name=str(entry.get("firstName") or "").strip(),
        last_name=str(entry.get("lastName") or "").strip(),
        middle_name=(entry.get("middleName") or "").strip() or None,
        role=str(entry.get("role") or "").strip(),
    )


class OrganizerSubmissionContentView(_StaffView):
    """``PUT staff/applications/{submission_id}/content`` — correct one entry in place."""

    def put(self, request: Request, submission_id: str) -> Response:
        serializer = OrganizerSubmissionContentSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        data = serializer.validated_data
        user_id = str(request.user.id)
        note = str(data.get("comment") or "").strip()

        performance = data.get("performance")
        command = EditSubmissionContentByOrganizerCommand(
            submission_id=submission_id,
            reviewer_id=user_id,
            performance=(
                OrganizerPerformanceInput(
                    title=str(performance["title"]).strip(),
                    duration_seconds=int(performance["durationSeconds"]),
                    nomination_id=str(performance["nominationId"]),
                    discipline_id=str(performance["disciplineId"]),
                    age_category_id=str(performance["ageCategoryId"]),
                    participant_group_id=str(performance["participantGroupId"]),
                    participation_format_id=str(performance["participationFormatId"]),
                    comment=str(performance.get("comment") or ""),
                    age_composition=str(performance.get("ageComposition") or ""),
                )
                if performance is not None
                else None
            ),
            participants=(tuple(_participant_input(entry) for entry in data["participants"]) if "participants" in data else None),
            teachers=(tuple(_teacher_input(entry) for entry in data["teachers"]) if "teachers" in data else None),
        )

        try:
            result = composition.build_edit_submission_content_by_organizer_handler().handle(command)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)

        names = _taxonomy_names(result.submission.competition_id) if result.changes else {}
        lines = [_change_line(change, names) for change in result.changes]
        if lines:
            self._record(submission_id=submission_id, user_id=user_id, lines=lines, note=note)
            self._tell_applicant(submission_id=submission_id, lines=lines, note=note, user_id=user_id)

        model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
        body = {
            "id": submission_id,
            "status": model.status,
            "capabilities": _capabilities(model.status),
            "changes": lines,
        }
        rid = problems.request_id(request)
        return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})

    @staticmethod
    def _record(*, submission_id: str, user_id: str, lines: list[str], note: str) -> None:
        """Write the correction into the entry's own record of being corrected."""
        model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
        edits = list(model.organizer_edits or [])
        edits.append(
            {
                "changes": lines,
                "comment": note,
                "created_by": user_id,
                "created_at": _now().isoformat(),
            }
        )
        model.organizer_edits = edits
        model.updated_at = _now()
        model.save(update_fields=["organizer_edits", "updated_at"])

    @staticmethod
    def _tell_applicant(*, submission_id: str, lines: list[str], note: str, user_id: str) -> None:
        """Tell the applicant what was changed on their behalf — letter, feed and journal.

        Never raises on their behalf either: the correction itself is already saved,
        and a mail backend having a bad minute must not turn a completed fix into a
        failed request the organizer will retry.
        """
        model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
        recipient = UserModel.objects.filter(id=model.applicant_id, deleted_at__isnull=True).first()
        application_id, _, competition_id = _application_meta_for_submission(submission_id)
        application_number = (application_id or submission_id)[:8].upper()
        competition_title = CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first() if competition_id else None
        changes_text = "\n".join(f"— {line}" for line in lines)

        messages = list(model.participant_messages or [])
        messages.append(
            {
                "text": f"Организатор исправил заявку #{application_number}:\n{changes_text}" + (f"\nПричина: {note}" if note else ""),
                "created_by": user_id,
                "created_at": _now().isoformat(),
            }
        )
        model.participant_messages = messages
        model.updated_at = _now()
        model.save(update_fields=["participant_messages", "updated_at"])

        if recipient is None or not recipient.email:
            return
        subject = f"Заявка #{application_number}: организатор внёс исправления"
        cabinet_url, detail_url = _application_urls(application_id)
        intro = (
            f"Организатор исправил данные в заявке #{application_number}"
            f"{f' ({competition_title})' if competition_title else ''}. Проверьте, всё ли верно."
        )
        body_text = (
            f"Здравствуйте, {recipient.first_name}!\n\n"
            f"{intro}\n\n"
            f"Что изменилось:\n{changes_text}\n\n"
            + (f"Комментарий организатора:\n{note}\n\n" if note else "")
            + f"Откройте заявку в личном кабинете: {detail_url}\n"
            f"Список заявок: {cabinet_url}\n\n"
            "Если исправление сделано по ошибке — напишите организатору.\n\n"
            "С уважением,\nОргкомитет фестиваля"
        )
        queue_review_email(
            subject=subject,
            body=body_text,
            to=recipient.email,
            html_body=render_transactional_email_html(
                title=subject,
                intro=intro,
                details_label="Что изменилось",
                details=changes_text + (f"\n\nКомментарий организатора: {note}" if note else ""),
                button_label="Открыть заявку в ЛК",
                button_url=detail_url,
                status="info",
                status_label="Исправлена",
            ),
        )
        notification_feed.publish(
            recipient_id=recipient.id,
            kind=NotificationKind.APPLICATION_CORRECTED,
            title=f"Заявка №{application_number}: внесены исправления",
            body=changes_text,
            link=_cabinet_path(application_id),
        )
