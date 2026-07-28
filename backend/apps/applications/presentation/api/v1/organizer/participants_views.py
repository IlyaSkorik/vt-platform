"""Organizer **Participant Registry** REST surface (read-only projection).

Exposes the automatically-derived registry of participants who have taken part
in the organization's competitions. There are **no** create/update/delete
endpoints — the registry is a projection of the Application/Submission context,
never edited directly (DATA-001, ARCH-001 §7.2). Every value (age, counts, full
name) is computed server-side; the client renders what it receives.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.application.read_models import (
    RegistryApplicationView,
    RegistryDocumentView,
    RegistryFilters,
    RegistryHistoryEntry,
    RegistryNoteView,
    RegistryOrganizationView,
    RegistryParticipantDetail,
    RegistryParticipantSummary,
    RegistryPerformanceView,
    RegistryTeacherView,
)
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.organizer.composition import (
    build_organizer_participant_registry,
    organization_competition_ids,
    organization_competitions,
)
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.organization.presentation.permissions import IsOrganizationStaff

_TAG = "Organizer Participants"


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)


def _int_param(raw: str | None) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _bool_param(raw: str | None) -> bool | None:
    text = (raw or "").strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def _filters_from_request(request: Request) -> RegistryFilters:
    params = request.query_params
    return RegistryFilters(
        query=(params.get("q") or "").strip() or None,
        gender=(params.get("gender") or "").strip() or None,
        age_min=_int_param(params.get("ageMin")),
        age_max=_int_param(params.get("ageMax")),
        competition_id=(params.get("competitionId") or "").strip() or None,
        organization=(params.get("organization") or "").strip() or None,
        participant_type=(params.get("participantType") or "").strip() or None,
        has_documents=_bool_param(params.get("hasDocuments")),
    )


def _envelope(request: Request, data: Any, *, meta: dict[str, Any] | None = None, status: int = 200) -> Response:
    request_id = problems.request_id(request)
    payload_meta = {"requestId": request_id}
    if meta:
        payload_meta.update(meta)
    return Response(
        {"data": data, "meta": payload_meta},
        status=status,
        headers={"X-Request-ID": request_id},
    )


def _organization_json(view: RegistryOrganizationView | None) -> dict[str, Any] | None:
    if view is None:
        return None
    return {"id": view.id, "name": view.name}


def _teacher_json(view: RegistryTeacherView) -> dict[str, Any]:
    return {"name": view.name, "role": view.role}


def _summary_json(summary: RegistryParticipantSummary) -> dict[str, Any]:
    return {
        "key": summary.key,
        "participantType": summary.participant_type,
        "displayName": summary.display_name,
        "firstName": summary.first_name,
        "lastName": summary.last_name,
        "middleName": summary.middle_name,
        "fullName": summary.full_name,
        "birthDate": summary.birth_date,
        "age": summary.age,
        "gender": summary.gender,
        "memberCount": summary.member_count,
        "primaryOrganization": _organization_json(summary.primary_organization),
        "organizations": [_organization_json(org) for org in summary.organizations],
        "teachers": [_teacher_json(teacher) for teacher in summary.teachers],
        "competitionsCount": summary.competitions_count,
        "applicationsCount": summary.applications_count,
        "performancesCount": summary.performances_count,
        "documentsCount": summary.documents_count,
        "lastActivity": summary.last_activity,
    }


def _application_json(view: RegistryApplicationView) -> dict[str, Any]:
    return {
        "submissionId": view.submission_id,
        "applicationId": view.application_id,
        "competitionId": view.competition_id,
        "competition": view.competition,
        "status": view.status,
        "performanceTitle": view.performance_title,
        "organization": view.organization,
        "teachers": [_teacher_json(teacher) for teacher in view.teachers],
        "submittedAt": view.submitted_at,
        "updatedAt": view.updated_at,
    }


def _performance_json(view: RegistryPerformanceView) -> dict[str, Any]:
    return {
        "submissionId": view.submission_id,
        "competitionId": view.competition_id,
        "competition": view.competition,
        "status": view.status,
        "title": view.title,
        "durationSeconds": view.duration_seconds,
        "nomination": view.nomination,
        "discipline": view.discipline,
        "ageCategory": view.age_category,
        "participantGroup": view.participant_group,
        "participationFormat": view.participation_format,
        "comment": view.comment,
    }


def _document_json(view: RegistryDocumentView) -> dict[str, Any]:
    return {
        "id": view.id,
        "submissionId": view.submission_id,
        "competition": view.competition,
        "type": view.type,
        "file": view.file,
        "caption": view.caption,
    }


def _history_json(view: RegistryHistoryEntry) -> dict[str, Any]:
    return {
        "submissionId": view.submission_id,
        "competitionId": view.competition_id,
        "competition": view.competition,
        "status": view.status,
        "date": view.date,
    }


def _note_json(view: RegistryNoteView) -> dict[str, Any]:
    return {
        "submissionId": view.submission_id,
        "competition": view.competition,
        "text": view.text,
        "createdAt": view.created_at,
    }


def _detail_json(detail: RegistryParticipantDetail) -> dict[str, Any]:
    return {
        **_summary_json(detail.summary),
        "applications": [_application_json(app) for app in detail.applications],
        "performances": [_performance_json(perf) for perf in detail.performances],
        "documents": [_document_json(doc) for doc in detail.documents],
        "history": [_history_json(entry) for entry in detail.history],
        "notes": [_note_json(note) for note in detail.notes],
        "awards": [
            {"title": award.title, "competition": award.competition, "date": award.date}
            for award in detail.awards
        ],
    }


def _facets(summaries: list[RegistryParticipantSummary]) -> dict[str, Any]:
    """Quick-filter counts, computed server-side over the competition scope."""
    return {
        "total": len(summaries),
        "solo": sum(1 for s in summaries if s.participant_type == "solo"),
        "collective": sum(1 for s in summaries if s.participant_type == "collective"),
        "withDocuments": sum(1 for s in summaries if s.documents_count > 0),
        "female": sum(1 for s in summaries if s.gender == "female"),
        "male": sum(1 for s in summaries if s.gender == "male"),
    }


class OrganizerParticipantRegistryCollectionView(_StaffView):
    @extend_schema(
        tags=[_TAG],
        operation_id="organizer_participant_registry_list",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="gender", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ageMin", type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ageMax", type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="competitionId", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="organization", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="participantType", type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="hasDocuments", type=bool, location=OpenApiParameter.QUERY),
        ],
    )
    def get(self, request: Request) -> Response:
        registry = build_organizer_participant_registry()
        scope = organization_competition_ids()
        filters = _filters_from_request(request)

        rows = registry.list(competition_ids=scope, filters=filters)
        # Quick-filter counts reflect the selected competition (if any) but not
        # the text/gender/age narrowing, so the chips stay stable as the user types.
        facet_source = registry.list(
            competition_ids=scope,
            filters=RegistryFilters(competition_id=filters.competition_id),
        )
        meta = {
            "total": len(rows),
            "facets": _facets(facet_source),
            "competitions": organization_competitions(),
        }
        return _envelope(request, [_summary_json(row) for row in rows], meta=meta)


class OrganizerParticipantRegistryDetailView(_StaffView):
    @extend_schema(tags=[_TAG], operation_id="organizer_participant_registry_detail")
    def get(self, request: Request, participant_key: str) -> Response:
        registry = build_organizer_participant_registry()
        scope = organization_competition_ids()
        detail = registry.get(competition_ids=scope, key=participant_key)
        if detail is None:
            return problems.problem_response(
                status=404,
                type_suffix="not-found",
                title="Resource not found",
                detail="Participant was not found in your organization's registry.",
                instance=request.path,
                correlation_id=problems.request_id(request),
            )
        return _envelope(request, _detail_json(detail))


class OrganizerParticipantRegistryExportView(_StaffView):
    @extend_schema(
        tags=[_TAG],
        operation_id="organizer_participant_registry_export",
        responses={200: OpenApiResponse(description="CSV export of the participant registry")},
    )
    def get(self, request: Request) -> Response:
        import csv
        from io import StringIO

        registry = build_organizer_participant_registry()
        scope = organization_competition_ids()
        rows = registry.list(competition_ids=scope, filters=_filters_from_request(request))

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "full_name",
                "type",
                "birth_date",
                "age",
                "gender",
                "primary_organization",
                "teachers",
                "competitions",
                "applications",
                "performances",
                "documents",
                "last_activity",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.full_name,
                    row.participant_type,
                    row.birth_date or "",
                    "" if row.age is None else row.age,
                    row.gender or "",
                    row.primary_organization.name if row.primary_organization else "",
                    "; ".join(teacher.name for teacher in row.teachers),
                    row.competitions_count,
                    row.applications_count,
                    row.performances_count,
                    row.documents_count,
                    row.last_activity,
                ]
            )
        response = Response(buffer.getvalue(), status=200, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="participants.csv"'
        response["X-Request-ID"] = problems.request_id(request)
        return response
