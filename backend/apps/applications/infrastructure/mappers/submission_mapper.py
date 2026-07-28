"""``SubmissionMapper`` - the ACL between the ``Submission`` aggregate and its ORM row.

The single component that knows both the framework-free domain and the Django
``SubmissionModel``. It serializes the aggregate's performance, child collections
and price snapshot to JSON-safe primitives and rehydrates them back via
:meth:`Submission.rehydrate` (no re-validation, no events). Datetimes are stored as
ISO-8601 strings and money amounts as decimal strings.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.applications.domain.entities import Attachment, Participant, Review, Submission, Teacher
from apps.applications.domain.value_objects import (
    AgeCategoryId,
    AttachmentId,
    AttachmentType,
    BirthDate,
    CompetitionId,
    Currency,
    DirectoryTeacherId,
    DisciplineId,
    Duration,
    FileReference,
    Gender,
    Money,
    NominationId,
    ParticipantGroupId,
    ParticipantId,
    ParticipationFormatId,
    Performance,
    PerformanceTitle,
    PersonName,
    PriceSnapshot,
    RegistryParticipantId,
    ReviewComment,
    ReviewerId,
    ReviewId,
    SubmissionId,
    SubmissionStatus,
    SubmissionStatusChange,
    TeacherId,
    TeacherRole,
    UserId,
)
from apps.applications.infrastructure.models import SubmissionModel

__all__ = ["SubmissionMapper"]


class SubmissionMapper:
    """Bidirectional, stateless translator between the ``Submission`` aggregate and its row."""

    @staticmethod
    def to_domain(model: SubmissionModel) -> Submission:
        """Reconstruct the ``Submission`` aggregate from its row (no re-validation, no events)."""
        return Submission.rehydrate(
            submission_id=SubmissionId.from_uuid(model.id),
            competition_id=CompetitionId.from_uuid(model.competition_id),
            applicant_id=UserId.from_uuid(model.applicant_id),
            status=SubmissionStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            performance=SubmissionMapper._performance_from_json(model.performance),
            participants=[SubmissionMapper._participant_from_json(row) for row in model.participants],
            teachers=[SubmissionMapper._teacher_from_json(row) for row in model.teachers],
            attachments=[SubmissionMapper._attachment_from_json(row) for row in model.attachments],
            reviews=[SubmissionMapper._review_from_json(row) for row in model.reviews],
            price_snapshot=SubmissionMapper._price_from_json(model.price_snapshot),
            status_history=[SubmissionMapper._status_change_from_json(row) for row in model.status_history],
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Submission) -> SubmissionModel:
        """Build a brand-new, **unsaved** ``SubmissionModel`` from an aggregate."""
        return SubmissionModel(**SubmissionMapper._to_columns(entity))

    @staticmethod
    def update_model(model: SubmissionModel, entity: Submission) -> SubmissionModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it."""
        for field, value in SubmissionMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    # ------------------------------------------------------------------
    # Aggregate -> columns
    # ------------------------------------------------------------------

    @staticmethod
    def _to_columns(entity: Submission) -> dict[str, Any]:
        performance = entity.performance
        price = entity.price_snapshot
        return {
            "id": entity.id.value,
            "competition_id": entity.competition_id.value,
            "applicant_id": entity.applicant_id.value,
            "status": entity.status.value,
            "performance": SubmissionMapper._performance_to_json(performance),
            "participants": [SubmissionMapper._participant_to_json(p) for p in entity.participants],
            "teachers": [SubmissionMapper._teacher_to_json(t) for t in entity.teachers],
            "attachments": [SubmissionMapper._attachment_to_json(a) for a in entity.attachments],
            "reviews": [SubmissionMapper._review_to_json(r) for r in entity.reviews],
            "price_snapshot": SubmissionMapper._price_to_json(price),
            "status_history": [SubmissionMapper._status_change_to_json(change) for change in entity.status_history],
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    @staticmethod
    def _performance_to_json(performance: Performance | None) -> dict[str, Any] | None:
        if performance is None:
            return None
        return {
            "title": performance.title.value,
            "duration_seconds": performance.duration.seconds,
            "nomination_id": performance.nomination_id.json(),
            "discipline_id": performance.discipline_id.json(),
            "age_category_id": performance.age_category_id.json(),
            "participant_group_id": performance.participant_group_id.json(),
            "participation_format_id": performance.participation_format_id.json(),
            "comment": performance.comment,
        }

    @staticmethod
    def _performance_from_json(data: dict[str, Any] | None) -> Performance | None:
        if data is None:
            return None
        return Performance(
            title=PerformanceTitle(data["title"]),
            duration=Duration.of_seconds(int(data["duration_seconds"])),
            nomination_id=NominationId.from_string(data["nomination_id"]),
            discipline_id=DisciplineId.from_string(data["discipline_id"]),
            age_category_id=AgeCategoryId.from_string(data["age_category_id"]),
            participant_group_id=ParticipantGroupId.from_string(data["participant_group_id"]),
            participation_format_id=ParticipationFormatId.from_string(data["participation_format_id"]),
            # Rows written before the comment existed simply have no key.
            comment=str(data.get("comment") or ""),
        )

    # ------------------------------------------------------------------
    # Children
    # ------------------------------------------------------------------

    @staticmethod
    def _participant_to_json(participant: Participant) -> dict[str, Any]:
        name = participant.name
        birth_date = participant.birth_date
        gender = participant.gender
        registry_id = participant.registry_participant_id
        return {
            "id": participant.id.json(),
            "display_name": participant.display_name,
            "first_name": name.first_name if name is not None else None,
            "last_name": name.last_name if name is not None else None,
            "middle_name": name.middle_name if name is not None else None,
            "birth_date": birth_date.value.isoformat() if birth_date is not None else None,
            "gender": gender.value if gender is not None else None,
            "registry_participant_id": registry_id.json() if registry_id is not None else None,
            "member_count": participant.member_count,
        }

    @staticmethod
    def _participant_from_json(data: dict[str, Any]) -> Participant:
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        name = PersonName(first_name=first_name, last_name=last_name, middle_name=data.get("middle_name")) if first_name and last_name else None
        birth_date_raw = data.get("birth_date")
        gender_raw = data.get("gender")
        registry_raw = data.get("registry_participant_id")
        return Participant.rehydrate(
            participant_id=ParticipantId.from_string(data["id"]),
            display_name=data.get("display_name"),
            name=name,
            birth_date=BirthDate(date.fromisoformat(birth_date_raw)) if birth_date_raw else None,
            gender=Gender(gender_raw) if gender_raw else None,
            registry_participant_id=RegistryParticipantId.from_string(registry_raw) if registry_raw else None,
            member_count=int(data.get("member_count", 1)),
        )

    @staticmethod
    def _teacher_to_json(teacher: Teacher) -> dict[str, Any]:
        directory_id = teacher.directory_teacher_id
        return {
            "id": teacher.id.json(),
            "first_name": teacher.name.first_name,
            "last_name": teacher.name.last_name,
            "middle_name": teacher.name.middle_name,
            "role": teacher.role.value,
            "directory_teacher_id": directory_id.json() if directory_id is not None else None,
        }

    @staticmethod
    def _teacher_from_json(data: dict[str, Any]) -> Teacher:
        directory_raw = data.get("directory_teacher_id")
        return Teacher.rehydrate(
            teacher_id=TeacherId.from_string(data["id"]),
            name=PersonName(first_name=data["first_name"], last_name=data["last_name"], middle_name=data["middle_name"]),
            role=TeacherRole(data["role"]),
            directory_teacher_id=DirectoryTeacherId.from_string(directory_raw) if directory_raw else None,
        )

    @staticmethod
    def _attachment_to_json(attachment: Attachment) -> dict[str, Any]:
        return {
            "id": attachment.id.json(),
            "type": attachment.type.value,
            "file": attachment.file.value,
            "caption": attachment.caption,
        }

    @staticmethod
    def _attachment_from_json(data: dict[str, Any]) -> Attachment:
        return Attachment.rehydrate(
            attachment_id=AttachmentId.from_string(data["id"]),
            attachment_type=AttachmentType(data["type"]),
            file=FileReference(data["file"]),
            caption=data["caption"],
        )

    @staticmethod
    def _review_to_json(review: Review) -> dict[str, Any]:
        return {
            "id": review.id.json(),
            "reviewer_id": review.reviewer_id.json(),
            "comment": review.comment.value,
            "created_at": review.created_at.isoformat(),
        }

    @staticmethod
    def _review_from_json(data: dict[str, Any]) -> Review:
        return Review.rehydrate(
            review_id=ReviewId.from_string(data["id"]),
            reviewer_id=ReviewerId.from_string(data["reviewer_id"]),
            comment=ReviewComment(data["comment"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Price snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def _price_to_json(price: PriceSnapshot | None) -> dict[str, Any] | None:
        if price is None:
            return None
        return {"amount": str(price.amount), "currency": price.currency.value, "calculated_at": price.calculated_at.isoformat()}

    @staticmethod
    def _price_from_json(data: dict[str, Any] | None) -> PriceSnapshot | None:
        if data is None:
            return None
        return PriceSnapshot(
            price=Money.of(data["amount"], Currency(data["currency"])),
            calculated_at=datetime.fromisoformat(data["calculated_at"]),
        )

    @staticmethod
    def _status_change_to_json(change: SubmissionStatusChange) -> dict[str, Any]:
        return {
            "from_status": change.from_status.value if change.from_status is not None else None,
            "to_status": change.to_status.value,
            "occurred_at": change.occurred_at.isoformat(),
        }

    @staticmethod
    def _status_change_from_json(data: dict[str, Any]) -> SubmissionStatusChange:
        return SubmissionStatusChange(
            from_status=SubmissionStatus(data["from_status"]) if data["from_status"] is not None else None,
            to_status=SubmissionStatus(data["to_status"]),
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
        )
