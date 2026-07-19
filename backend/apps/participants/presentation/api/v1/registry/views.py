from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.participants.infrastructure.models import (
    EducationalOrganizationModel,
    ParticipantOrganizationMembershipModel,
    ParticipantRegistryModel,
)
from apps.participants.presentation.api.v1 import problems
from apps.participants.presentation.api.v1.registry.serializers import (
    OrganizationWriteSerializer,
    ParticipantRegistryWriteSerializer,
)

_TAG = "Participants"


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _owner_uuid(raw_user_id: object) -> uuid.UUID:
    text = str(raw_user_id).strip()
    try:
        return uuid.UUID(text)
    except ValueError:
        # Support non-UUID auth subjects by deriving a deterministic UUID.
        return uuid.uuid5(uuid.NAMESPACE_URL, f"participant-owner:{text}")


def _age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _organization_resource(model: EducationalOrganizationModel) -> dict[str, Any]:
    return {
        "id": str(model.id),
        "name": model.name,
        "type": model.organization_type,
        "country": model.country,
        "city": model.city,
        "address": model.address,
        "website": model.website,
        "archived": model.deleted_at is not None,
    }


def _participant_resource(model: ParticipantRegistryModel, *, applications_count: int = 0) -> dict[str, Any]:
    memberships = list(
        model.organization_memberships.select_related("organization")
        .filter(deleted_at__isnull=True, organization__deleted_at__isnull=True)
        .order_by("-is_primary", "organization__name")
    )
    primary_membership = next((membership for membership in memberships if membership.is_primary), None)
    full_name = (
        (model.collective_name or "").strip()
        if model.participant_type == "collective"
        else " ".join(part for part in [model.last_name, model.first_name, model.middle_name] if part)
    )
    return {
        "id": str(model.id),
        "participantType": model.participant_type,
        "collectiveName": model.collective_name,
        "firstName": model.first_name,
        "lastName": model.last_name,
        "middleName": model.middle_name,
        "fullName": full_name,
        "birthDate": model.birth_date.isoformat(),
        "age": _age(model.birth_date),
        "gender": model.gender,
        "avatarUrl": model.avatar_url,
        "notes": model.notes,
        "archived": model.archived,
        "applicationsCount": applications_count,
        "primaryOrganization": _organization_resource(primary_membership.organization)
        if primary_membership is not None
        else None,
        "organizations": [
            {
                **_organization_resource(membership.organization),
                "isPrimary": membership.is_primary,
            }
            for membership in memberships
        ],
        "createdAt": model.created_at.isoformat().replace("+00:00", "Z"),
        "updatedAt": model.updated_at.isoformat().replace("+00:00", "Z"),
    }


def _envelope(request: Request, data: Any, *, status: int = 200) -> Response:
    request_id = problems.request_id(request)
    return Response(
        {"data": data, "meta": {"requestId": request_id}},
        status=status,
        headers={"X-Request-ID": request_id},
    )


def _applications_count_by_participant(*, owner_id: uuid.UUID, participant_ids: set[str]) -> dict[str, int]:
    if not participant_ids:
        return {}

    submission_participants: dict[str, set[str]] = {}
    submissions = SubmissionModel.objects.filter(
        deleted_at__isnull=True,
        applicant_id=owner_id,
    ).values("id", "participants")
    for row in submissions:
        submission_id = str(row.get("id"))
        participant_refs = {
            str(item.get("registry_participant_id") or "").strip()
            for item in (row.get("participants") or [])
            if str(item.get("registry_participant_id") or "").strip()
        }
        if participant_refs:
            submission_participants[submission_id] = participant_refs

    counts = dict.fromkeys(participant_ids, 0)
    applications = ApplicationModel.objects.filter(
        deleted_at__isnull=True,
        applicant_id=owner_id,
    ).exclude(status="DRAFT").values("submission_refs")
    for row in applications:
        refs = row.get("submission_refs") or []
        touched: set[str] = set()
        for ref in refs:
            submission_id = str(ref.get("submission_id") or "")
            touched.update(submission_participants.get(submission_id, set()))
        for participant_id in touched:
            if participant_id in counts:
                counts[participant_id] += 1
    return counts


def _save_memberships(
    *,
    request: Request,
    owner_id: uuid.UUID,
    participant: ParticipantRegistryModel,
    organizations: list[dict[str, Any]],
) -> Response | None:
    if not organizations:
        return problems.problem_response(
            status=400,
            type_suffix="validation-error",
            title="Validation failed",
            detail="At least one educational organization is required.",
            instance=request.path,
            correlation_id=problems.request_id(request),
            errors=[{"pointer": "/organizations", "code": "required", "detail": "Provide organizations."}],
        )
    primary_count = sum(1 for item in organizations if bool(item.get("isPrimary")))
    if primary_count != 1:
        return problems.problem_response(
            status=400,
            type_suffix="validation-error",
            title="Validation failed",
            detail="Exactly one organization must be marked as primary.",
            instance=request.path,
            correlation_id=problems.request_id(request),
            errors=[{"pointer": "/organizations", "code": "primary_invalid", "detail": "Select one primary."}],
        )
    organization_ids = [str(item["organizationId"]) for item in organizations]
    organizations_by_id = {
        str(item.id): item
        for item in EducationalOrganizationModel.objects.filter(
            owner_id=owner_id,
            deleted_at__isnull=True,
            id__in=organization_ids,
        )
    }
    if len(organizations_by_id) != len(set(organization_ids)):
        return problems.problem_response(
            status=400,
            type_suffix="validation-error",
            title="Validation failed",
            detail="One or more organizations do not exist in your directory.",
            instance=request.path,
            correlation_id=problems.request_id(request),
            errors=[
                {
                    "pointer": "/organizations",
                    "code": "unknown_organization",
                    "detail": "Use organizations from your personal directory only.",
                }
            ],
        )
    participant.organization_memberships.all().delete()
    ParticipantOrganizationMembershipModel.objects.bulk_create(
        [
            ParticipantOrganizationMembershipModel(
                participant=participant,
                organization=organizations_by_id[str(item["organizationId"])],
                is_primary=bool(item["isPrimary"]),
            )
            for item in organizations
        ]
    )
    return None


def _validate_participant_payload(payload: dict[str, Any], request: Request) -> Response | None:
    participant_type = str(payload.get("participantType") or "solo")
    collective_name = _optional_str(payload.get("collectiveName"))
    first_name = str(payload.get("firstName") or "").strip()
    last_name = str(payload.get("lastName") or "").strip()
    birth_date = payload.get("birthDate")
    gender = payload.get("gender")
    if participant_type == "collective":
        if collective_name is None:
            return problems.problem_response(
                status=400,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Для коллектива укажите название.",
                instance=request.path,
                correlation_id=problems.request_id(request),
                errors=[
                    {
                        "pointer": "/collectiveName",
                        "code": "required",
                        "detail": "Введите название коллектива.",
                    }
                ],
            )
    else:
        if not first_name or not last_name:
            return problems.problem_response(
                status=400,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Для сольного участника укажите имя и фамилию.",
                instance=request.path,
                correlation_id=problems.request_id(request),
                errors=[
                    {"pointer": "/firstName", "code": "required", "detail": "Укажите имя."},
                    {"pointer": "/lastName", "code": "required", "detail": "Укажите фамилию."},
                ],
            )
        if birth_date is None or gender is None:
            return problems.problem_response(
                status=400,
                type_suffix="validation-error",
                title="Validation failed",
                detail="Для сольного участника укажите дату рождения и пол.",
                instance=request.path,
                correlation_id=problems.request_id(request),
                errors=[
                    {"pointer": "/birthDate", "code": "required", "detail": "Укажите дату рождения."},
                    {"pointer": "/gender", "code": "required", "detail": "Укажите пол."},
                ],
            )
    return None


class _AuthView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated,)


class ParticipantRegistryCollectionView(_AuthView):
    @extend_schema(
        tags=[_TAG],
        operation_id="participant_registry_list",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="organizationId", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="city", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="gender", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="archived", type=bool, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ageMin", type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ageMax", type=int, location=OpenApiParameter.QUERY),
        ],
    )
    def get(self, request: Request) -> Response:
        owner_id = _owner_uuid(request.user.id)
        qs = ParticipantRegistryModel.objects.filter(owner_id=owner_id, deleted_at__isnull=True).order_by(
            "-updated_at"
        )
        search = _optional_str(request.query_params.get("q"))
        if search is not None:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(middle_name__icontains=search)
                | Q(collective_name__icontains=search)
                | Q(
                    organization_memberships__organization__name__icontains=search,
                    organization_memberships__deleted_at__isnull=True,
                    organization_memberships__organization__deleted_at__isnull=True,
                )
            )
        city = _optional_str(request.query_params.get("city"))
        if city is not None:
            qs = qs.filter(
                organization_memberships__organization__city__icontains=city,
                organization_memberships__deleted_at__isnull=True,
                organization_memberships__organization__deleted_at__isnull=True,
            )
        gender = _optional_str(request.query_params.get("gender"))
        if gender is not None:
            qs = qs.filter(gender=gender)
        archived = _optional_str(request.query_params.get("archived"))
        if archived is not None:
            qs = qs.filter(archived=archived.lower() in {"1", "true", "yes"})

        organization_id = _optional_str(request.query_params.get("organizationId"))
        if organization_id is not None:
            qs = qs.filter(
                organization_memberships__organization_id=organization_id,
                organization_memberships__deleted_at__isnull=True,
            )

        today = date.today()
        age_min_raw = _optional_str(request.query_params.get("ageMin"))
        age_max_raw = _optional_str(request.query_params.get("ageMax"))
        if age_min_raw is not None:
            age_min = int(age_min_raw)
            max_birth = date(today.year - age_min, today.month, today.day)
            qs = qs.filter(birth_date__lte=max_birth)
        if age_max_raw is not None:
            age_max = int(age_max_raw)
            min_birth = date(today.year - age_max - 1, today.month, today.day)
            qs = qs.filter(birth_date__gte=min_birth)

        models = list(qs.distinct())
        app_counts = _applications_count_by_participant(
            owner_id=owner_id,
            participant_ids={str(model.id) for model in models},
        )
        data = [
            _participant_resource(model, applications_count=app_counts.get(str(model.id), 0))
            for model in models
        ]
        return _envelope(request, data)

    @extend_schema(tags=[_TAG], request=ParticipantRegistryWriteSerializer)
    def post(self, request: Request) -> Response:
        serializer = ParticipantRegistryWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        owner_id = _owner_uuid(request.user.id)
        payload = serializer.validated_data
        payload_problem = _validate_participant_payload(payload, request)
        if payload_problem is not None:
            return payload_problem
        with transaction.atomic():
            participant_type = str(payload.get("participantType") or "solo")
            first_name = "" if participant_type == "collective" else str(payload.get("firstName") or "").strip()
            last_name = "" if participant_type == "collective" else str(payload.get("lastName") or "").strip()
            middle_name = None if participant_type == "collective" else _optional_str(payload.get("middleName"))
            birth_date = payload.get("birthDate") or date.today()
            gender = str(payload.get("gender") or "other")
            participant = ParticipantRegistryModel.objects.create(
                owner_id=owner_id,
                participant_type=participant_type,
                collective_name=_optional_str(payload.get("collectiveName")),
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                birth_date=birth_date,
                gender=gender,
                avatar_url=_optional_str(payload.get("avatarUrl")),
                notes=str(payload.get("notes") or "").strip(),
            )
            membership_problem = _save_memberships(
                request=request,
                owner_id=owner_id,
                participant=participant,
                organizations=list(payload["organizations"]),
            )
            if membership_problem is not None:
                transaction.set_rollback(True)
                return membership_problem
        participant.refresh_from_db()
        app_counts = _applications_count_by_participant(owner_id=owner_id, participant_ids={str(participant.id)})
        return _envelope(
            request,
            _participant_resource(participant, applications_count=app_counts.get(str(participant.id), 0)),
            status=201,
        )


class ParticipantRegistryDetailView(_AuthView):
    def get_object(self, *, owner_id: uuid.UUID, participant_id: str) -> ParticipantRegistryModel | None:
        return ParticipantRegistryModel.objects.filter(
            id=participant_id,
            owner_id=owner_id,
            deleted_at__isnull=True,
        ).first()

    @extend_schema(tags=[_TAG])
    def get(self, request: Request, participant_id: str) -> Response:
        participant = self.get_object(owner_id=_owner_uuid(request.user.id), participant_id=participant_id)
        if participant is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Participant was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        owner_id = _owner_uuid(request.user.id)
        app_counts = _applications_count_by_participant(owner_id=owner_id, participant_ids={str(participant.id)})
        return _envelope(request, _participant_resource(participant, applications_count=app_counts.get(str(participant.id), 0)))

    @extend_schema(tags=[_TAG], request=ParticipantRegistryWriteSerializer)
    def patch(self, request: Request, participant_id: str) -> Response:
        owner_id = _owner_uuid(request.user.id)
        participant = self.get_object(owner_id=owner_id, participant_id=participant_id)
        if participant is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Participant was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        serializer = ParticipantRegistryWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        payload = serializer.validated_data
        payload_problem = _validate_participant_payload(payload, request)
        if payload_problem is not None:
            return payload_problem
        with transaction.atomic():
            participant.participant_type = str(payload.get("participantType") or "solo")
            participant.collective_name = _optional_str(payload.get("collectiveName"))
            if participant.participant_type == "collective":
                participant.first_name = ""
                participant.last_name = ""
                participant.middle_name = None
            else:
                participant.first_name = str(payload.get("firstName") or "").strip()
                participant.last_name = str(payload.get("lastName") or "").strip()
                participant.middle_name = _optional_str(payload.get("middleName"))
            participant.birth_date = payload.get("birthDate") or participant.birth_date
            participant.gender = str(payload.get("gender") or participant.gender)
            participant.avatar_url = _optional_str(payload.get("avatarUrl"))
            participant.notes = str(payload.get("notes") or "").strip()
            participant.save()
            membership_problem = _save_memberships(
                request=request,
                owner_id=owner_id,
                participant=participant,
                organizations=list(payload["organizations"]),
            )
            if membership_problem is not None:
                transaction.set_rollback(True)
                return membership_problem
        participant.refresh_from_db()
        app_counts = _applications_count_by_participant(owner_id=owner_id, participant_ids={str(participant.id)})
        return _envelope(request, _participant_resource(participant, applications_count=app_counts.get(str(participant.id), 0)))

    @extend_schema(tags=[_TAG], request=None, responses={204: OpenApiResponse(description="Deleted")})
    def delete(self, request: Request, participant_id: str) -> Response:
        participant = self.get_object(owner_id=_owner_uuid(request.user.id), participant_id=participant_id)
        if participant is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Participant was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        participant.delete()
        return Response(status=204)


class ParticipantArchiveView(_AuthView):
    @extend_schema(tags=[_TAG], request=None)
    def post(self, request: Request, participant_id: str) -> Response:
        participant = ParticipantRegistryModel.objects.filter(
            id=participant_id,
            owner_id=_owner_uuid(request.user.id),
            deleted_at__isnull=True,
        ).first()
        if participant is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Participant was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        owner_id = _owner_uuid(request.user.id)
        participant.archived = not participant.archived
        participant.save(update_fields=["archived", "updated_at"])
        app_counts = _applications_count_by_participant(owner_id=owner_id, participant_ids={str(participant.id)})
        return _envelope(request, _participant_resource(participant, applications_count=app_counts.get(str(participant.id), 0)))


class EducationalOrganizationCollectionView(_AuthView):
    @extend_schema(tags=[_TAG])
    def get(self, request: Request) -> Response:
        owner_id = _owner_uuid(request.user.id)
        search = _optional_str(request.query_params.get("q"))
        include_archived = (_optional_str(request.query_params.get("includeArchived")) or "").lower() in {
            "1",
            "true",
            "yes",
        }
        qs = EducationalOrganizationModel.objects.filter(owner_id=owner_id)
        if not include_archived:
            qs = qs.filter(deleted_at__isnull=True)
        qs = qs.order_by("name")
        if search is not None:
            qs = qs.filter(Q(name__icontains=search) | Q(city__icontains=search))
        used_subquery = ParticipantOrganizationMembershipModel.objects.filter(
            organization_id=OuterRef("id"),
            deleted_at__isnull=True,
            participant__deleted_at__isnull=True,
        )
        qs = qs.annotate(
            participantsCount=Count(
                "participant_memberships",
                filter=Q(participant_memberships__deleted_at__isnull=True),
            ),
            isUsed=Exists(used_subquery),
        )
        data = [
            {
                **_organization_resource(model),
                "participantsCount": int(getattr(model, "participantsCount", 0)),
                "isUsed": bool(getattr(model, "isUsed", False)),
            }
            for model in qs
        ]
        return _envelope(request, data)

    @extend_schema(tags=[_TAG], request=OrganizationWriteSerializer)
    def post(self, request: Request) -> Response:
        serializer = OrganizationWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        owner_id = _owner_uuid(request.user.id)
        payload = serializer.validated_data
        name = str(payload["name"]).strip()
        existing = EducationalOrganizationModel.objects.filter(
            owner_id=owner_id,
            deleted_at__isnull=True,
            name=name,
        ).first()
        if existing is not None:
            return problems.problem_response(
                status=409,
                type_suffix="conflict",
                title="Organization already exists",
                detail="An organization with this name already exists in your directory.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        organization = EducationalOrganizationModel.objects.create(
            owner_id=owner_id,
            name=name,
            organization_type=str(payload["type"]),
            country=_optional_str(payload.get("country")),
            city=_optional_str(payload.get("city")),
            address=_optional_str(payload.get("address")),
            website=_optional_str(payload.get("website")),
        )
        return _envelope(request, _organization_resource(organization), status=201)


class EducationalOrganizationDetailView(_AuthView):
    def get_object(self, *, owner_id: uuid.UUID, organization_id: str) -> EducationalOrganizationModel | None:
        return EducationalOrganizationModel.objects.filter(
            id=organization_id,
            owner_id=owner_id,
        ).first()

    @extend_schema(tags=[_TAG], request=OrganizationWriteSerializer)
    def patch(self, request: Request, organization_id: str) -> Response:
        owner_id = _owner_uuid(request.user.id)
        organization = self.get_object(owner_id=owner_id, organization_id=organization_id)
        if organization is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Organization was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        serializer = OrganizationWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return problems.validation_problem(serializer.errors, instance=request.path, request=request)
        payload = serializer.validated_data
        new_name = str(payload["name"]).strip()
        duplicate = EducationalOrganizationModel.objects.filter(
            owner_id=owner_id,
            deleted_at__isnull=True,
            name=new_name,
        ).exclude(id=organization.id)
        if duplicate.exists():
            return problems.problem_response(
                status=409,
                type_suffix="conflict",
                title="Organization already exists",
                detail="An organization with this name already exists in your directory.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        organization.name = new_name
        organization.organization_type = str(payload["type"])
        organization.country = _optional_str(payload.get("country"))
        organization.city = _optional_str(payload.get("city"))
        organization.address = _optional_str(payload.get("address"))
        organization.website = _optional_str(payload.get("website"))
        organization.save()
        return _envelope(request, _organization_resource(organization), status=200)


class EducationalOrganizationArchiveView(_AuthView):
    @extend_schema(tags=[_TAG], request=None)
    def post(self, request: Request, organization_id: str) -> Response:
        owner_id = _owner_uuid(request.user.id)
        organization = EducationalOrganizationModel.objects.filter(
            id=organization_id,
            owner_id=owner_id,
        ).first()
        if organization is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Organization was not found.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        if organization.deleted_at is None:
            organization.deleted_at = timezone.now()
        else:
            organization.deleted_at = None
        organization.save(update_fields=["deleted_at", "updated_at"])
        return _envelope(
            request,
            {
                **_organization_resource(organization),
                "archived": organization.deleted_at is not None,
            },
            status=200,
        )
