from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from apps.applications.application.dto.commands import (
    AcceptSubmissionCommand,
    ApproveSubmissionCommand,
    CancelSubmissionByReviewerCommand,
    CompleteSubmissionCommand,
    MarkPaidCommand,
    MarkWaitingPaymentCommand,
    ReturnSubmissionForCorrectionCommand,
    ScheduleSubmissionCommand,
    StartReviewCommand,
)
from apps.applications.application.dto.queries import GetSubmissionQuery
from apps.applications.application.exceptions import ApplicationError
from apps.applications.infrastructure.models.application import ApplicationModel
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.applications.presentation.api.v1 import problems
from apps.applications.presentation.api.v1.submissions import composition
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.organization.presentation.permissions import IsOrganizationStaff

_QUEUE_BY_STATUS = {
    "SUBMITTED": "NEW",
    "UNDER_REVIEW": "NEW",
    "REQUIRES_CORRECTION": "RETURNED",
    "APPROVED": "WAITING_PAYMENT",
    "WAITING_PAYMENT": "WAITING_PAYMENT",
    "PAID": "READY",
    "ACCEPTED": "READY",
    "SCHEDULED": "RUNNING",
    "COMPLETED": "COMPLETED",
    "CANCELLED": "ARCHIVE",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _payment_status(status: str) -> str:
    if status in {"WAITING_PAYMENT"}:
        return "WAITING"
    if status in {"PAID", "ACCEPTED", "SCHEDULED", "COMPLETED"}:
        return "PAID"
    return "NOT_REQUESTED"


def _capabilities(status: str) -> list[dict[str, str]]:
    mapping: dict[str, list[tuple[str, str]]] = {
        "SUBMITTED": [("start_review", "Начать проверку"), ("cancel", "Отменить")],
        "UNDER_REVIEW": [("approve", "Одобрить"), ("return_for_correction", "Вернуть на исправление"), ("cancel", "Отменить")],
        "REQUIRES_CORRECTION": [],
        "APPROVED": [("request_payment", "Запросить оплату"), ("cancel", "Отменить")],
        "WAITING_PAYMENT": [("confirm_payment", "Подтвердить оплату"), ("cancel", "Отменить")],
        "PAID": [("confirm_participation", "Подтвердить участие")],
        "ACCEPTED": [("move_to_running", "Перевести в конкурс")],
        "SCHEDULED": [("mark_completed", "Завершить")],
        "COMPLETED": [],
        "CANCELLED": [],
    }
    return [{"key": key, "label": label} for key, label in mapping.get(status, [])]


class _StaffView(APIView):
    authentication_classes = (JWTStatelessUserAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff)


class OrganizerProcessingWorkspaceView(_StaffView):
    def get(self, request: Request) -> Response:
        user_id = str(request.user.id)
        query = (request.query_params.get("q") or "").strip().lower()
        queue_filter = (request.query_params.get("queue") or "").strip().upper()
        selected_id = (request.query_params.get("selected") or "").strip()
        competition_filter = (request.query_params.get("competitionId") or "").strip()
        status_filter = (request.query_params.get("status") or "").strip().upper()
        payment_filter = (request.query_params.get("payment") or "").strip().upper()
        teacher_filter = (request.query_params.get("teacher") or "").strip().lower()
        organization_filter = (request.query_params.get("organization") or "").strip().lower()
        from_date = (request.query_params.get("from") or "").strip()
        to_date = (request.query_params.get("to") or "").strip()
        has_corrections_filter = (request.query_params.get("hasCorrections") or "").strip().lower()
        has_missing_files_filter = (request.query_params.get("hasMissingFiles") or "").strip().lower()

        competitions = list(
            CompetitionModel.objects.filter(deleted_at__isnull=True).values("id", "title", "status").order_by("title")
        )
        competition_name = {str(row["id"]): row["title"] for row in competitions}
        organization_by_submission: dict[str, str] = {}
        application_rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values("organization_name", "submission_refs")
        for row in application_rows:
            organization_name = str(row.get("organization_name") or "")
            for ref in row.get("submission_refs") or []:
                submission_id = str(ref.get("submission_id") or "")
                if submission_id:
                    organization_by_submission[submission_id] = organization_name

        submissions = list(
            SubmissionModel.objects.filter(
                deleted_at__isnull=True,
                competition_id__in=[row["id"] for row in competitions],
                status__in=list(_QUEUE_BY_STATUS),
            ).order_by("-updated_at")
        )

        rows: list[dict[str, Any]] = []
        for model in submissions:
            performance = model.performance or {}
            participants = model.participants or []
            teachers = model.teachers or []
            missing_requests = model.missing_files_requests or []
            has_missing_files = any(not bool(entry.get("resolved_at")) for entry in missing_requests)
            queue_key = _QUEUE_BY_STATUS.get(model.status, "ARCHIVE")
            if has_missing_files and model.status not in {"COMPLETED", "CANCELLED"}:
                queue_key = "WAITING_FILES"
            title = str(performance.get("title") or "")
            applicant = str(model.applicant_id)
            organization_name = organization_by_submission.get(str(model.id), "")
            teachers_text = " ".join(
                " ".join(filter(None, [str(item.get("last_name") or ""), str(item.get("first_name") or "")])).strip()
                for item in teachers
            )
            haystack = " ".join(
                [str(model.id), title, applicant, competition_name.get(str(model.competition_id), ""), organization_name, teachers_text]
            ).lower()
            if query and query not in haystack:
                continue
            if queue_filter and queue_key != queue_filter:
                continue
            if competition_filter and str(model.competition_id) != competition_filter:
                continue
            if status_filter and model.status != status_filter:
                continue
            payment = _payment_status(model.status)
            if payment_filter and payment != payment_filter:
                continue
            if teacher_filter and teacher_filter not in teachers_text.lower():
                continue
            if organization_filter and organization_filter not in organization_name.lower():
                continue
            if from_date and model.created_at.date().isoformat() < from_date:
                continue
            if to_date and model.created_at.date().isoformat() > to_date:
                continue
            has_corrections = model.status == "REQUIRES_CORRECTION"
            if has_corrections_filter in {"true", "false"} and has_corrections != (has_corrections_filter == "true"):
                continue
            if has_missing_files_filter in {"true", "false"} and has_missing_files != (has_missing_files_filter == "true"):
                continue
            rows.append(
                {
                    "id": str(model.id),
                    "applicationNumber": str(model.id)[:8].upper(),
                    "competitionId": str(model.competition_id),
                    "competition": competition_name.get(str(model.competition_id), "—"),
                    "applicant": applicant,
                    "performancesCount": 1,
                    "participantsCount": sum(int(item.get("member_count", 1)) for item in participants),
                    "status": model.status,
                    "queue": queue_key,
                    "paymentStatus": payment,
                    "organization": organization_name or None,
                    "submissionDate": model.created_at,
                    "lastActivity": model.updated_at,
                    "badges": {
                        "hasCorrections": has_corrections,
                        "hasMissingFiles": has_missing_files,
                    },
                    "capabilities": _capabilities(model.status),
                }
            )

        queue_counts = Counter(item["queue"] for item in rows)
        selected = next((item for item in rows if item["id"] == selected_id), rows[0] if rows else None)
        detail: dict[str, Any] | None = None
        if selected is not None:
            try:
                dto = composition.build_get_submission_handler().handle(
                    GetSubmissionQuery(submission_id=selected["id"], requested_by=user_id)
                )
            except ApplicationError:
                detail = None
            else:
                detail = {
                    "id": dto.id,
                    "status": dto.status,
                    "performance": dto.performance.title if dto.performance else None,
                    "participants": [
                        {"id": p.id, "name": p.display_name, "memberCount": p.member_count} for p in dto.participants
                    ],
                    "teachers": [{"id": t.id, "name": f"{t.last_name} {t.first_name}", "role": t.role} for t in dto.teachers],
                    "attachments": [{"id": a.id, "type": a.type, "fileReference": a.file_reference} for a in dto.attachments],
                    "price": dto.price.amount if dto.price else None,
                    "timeline": [
                        *[
                            {
                                "kind": "transition",
                                "label": f"{from_status or 'NONE'} -> {to_status}",
                                "at": occurred_at,
                            }
                            for from_status, to_status, occurred_at in dto.status_history
                        ],
                        *[
                            {"kind": "review", "label": review.comment, "at": review.created_at}
                            for review in dto.reviews
                        ],
                        *[
                            {
                                "kind": "missing_files",
                                "label": f"Запрошены файлы: {', '.join(entry.get('types', []))}",
                                "at": entry.get("created_at"),
                            }
                            for entry in (
                                SubmissionModel.objects.filter(id=selected["id"])
                                .values_list("missing_files_requests", flat=True)
                                .first()
                                or []
                            )
                        ],
                    ],
                    "audit": [
                        {
                            "at": review.created_at,
                            "by": review.reviewer_id,
                            "reason": review.comment,
                        }
                        for review in dto.reviews
                    ],
                    "internalNotes": SubmissionModel.objects.filter(id=selected["id"]).values_list("organizer_notes", flat=True).first()
                    or [],
                    "participantMessages": SubmissionModel.objects.filter(id=selected["id"]).values_list(
                        "participant_messages", flat=True
                    ).first()
                    or [],
                }

        payload = {
            "queues": [
                {"key": "NEW", "label": "Новые заявки", "count": queue_counts.get("NEW", 0)},
                {"key": "RETURNED", "label": "Возвращены на исправление", "count": queue_counts.get("RETURNED", 0)},
                {"key": "WAITING_FILES", "label": "Ожидают файлы", "count": queue_counts.get("WAITING_FILES", 0)},
                {"key": "WAITING_PAYMENT", "label": "Ожидают оплату", "count": queue_counts.get("WAITING_PAYMENT", 0)},
                {"key": "READY", "label": "Готовы к конкурсу", "count": queue_counts.get("READY", 0)},
                {"key": "RUNNING", "label": "Конкурс идет", "count": queue_counts.get("RUNNING", 0)},
                {"key": "COMPLETED", "label": "Завершены", "count": queue_counts.get("COMPLETED", 0)},
                {"key": "ARCHIVE", "label": "Архив", "count": queue_counts.get("ARCHIVE", 0)},
            ],
            "metrics": {
                "needReview": queue_counts.get("NEW", 0),
                "needCorrection": queue_counts.get("RETURNED", 0),
                "needPayment": queue_counts.get("WAITING_PAYMENT", 0),
                "ready": queue_counts.get("READY", 0),
                "running": queue_counts.get("RUNNING", 0),
                "completed": queue_counts.get("COMPLETED", 0),
            },
            "competitions": [{"id": str(row["id"]), "title": row["title"], "status": row["status"]} for row in competitions],
            "applications": rows,
            "selected": selected["id"] if selected else None,
            "detail": detail,
        }
        rid = problems.request_id(request)
        return Response({"data": payload, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})


class OrganizerProcessingActionView(_StaffView):
    def post(self, request: Request, submission_id: str, action: str) -> Response:
        user_id = str(request.user.id)
        comment = str(request.data.get("comment", "")).strip()
        try:
            if action == "start_review":
                result = composition.build_start_review_handler().handle(
                    StartReviewCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "approve":
                result = composition.build_approve_submission_handler().handle(
                    ApproveSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "return_for_correction":
                result = composition.build_return_for_correction_handler().handle(
                    ReturnSubmissionForCorrectionCommand(
                        submission_id=submission_id,
                        reviewer_id=user_id,
                        comment=comment or "Требуется исправление",
                    )
                )
            elif action == "request_payment":
                result = composition.build_mark_waiting_payment_handler().handle(
                    MarkWaitingPaymentCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "confirm_payment":
                result = composition.build_mark_paid_handler().handle(
                    MarkPaidCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "confirm_participation":
                result = composition.build_accept_submission_handler().handle(
                    AcceptSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "move_to_running":
                result = composition.build_schedule_submission_handler().handle(
                    ScheduleSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "mark_completed":
                result = composition.build_complete_submission_handler().handle(
                    CompleteSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "cancel":
                result = composition.build_cancel_submission_by_reviewer_handler().handle(
                    CancelSubmissionByReviewerCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "request_missing_files":
                missing_types = request.data.get("types") or []
                if not isinstance(missing_types, list):
                    return Response({"detail": "types must be list"}, status=400)
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                requests = list(model.missing_files_requests or [])
                requests.append(
                    {
                        "id": f"mf-{len(requests) + 1}",
                        "types": [str(item).upper() for item in missing_types],
                        "message": comment or None,
                        "created_by": user_id,
                        "created_at": _now().isoformat(),
                        "resolved_at": None,
                    }
                )
                model.missing_files_requests = requests
                model.updated_at = _now()
                model.save(update_fields=["missing_files_requests", "updated_at"])
                body = {"id": submission_id, "status": model.status, "capabilities": _capabilities(model.status)}
                rid = problems.request_id(request)
                return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})
            elif action == "add_internal_note":
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                notes = list(model.organizer_notes or [])
                notes.append({"text": comment, "created_by": user_id, "created_at": _now().isoformat()})
                model.organizer_notes = notes
                model.updated_at = _now()
                model.save(update_fields=["organizer_notes", "updated_at"])
                body = {"id": submission_id, "status": model.status, "capabilities": _capabilities(model.status)}
                rid = problems.request_id(request)
                return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})
            elif action == "send_participant_message":
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                messages = list(model.participant_messages or [])
                messages.append({"text": comment, "created_by": user_id, "created_at": _now().isoformat()})
                model.participant_messages = messages
                model.updated_at = _now()
                model.save(update_fields=["participant_messages", "updated_at"])
                body = {"id": submission_id, "status": model.status, "capabilities": _capabilities(model.status)}
                rid = problems.request_id(request)
                return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})
            else:
                return Response({"detail": "Unknown action."}, status=400)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)

        body = {"id": result.submission.id, "status": result.submission.status, "capabilities": _capabilities(result.submission.status)}
        rid = problems.request_id(request)
        return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})


class OrganizerProcessingBulkView(_StaffView):
    def post(self, request: Request) -> Response:
        action = str(request.data.get("action") or "").strip()
        ids = request.data.get("ids") or []
        comment = str(request.data.get("comment", "")).strip()
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids required"}, status=400)
        processed: list[str] = []
        failed: list[dict[str, str]] = []
        for submission_id in [str(item) for item in ids]:
            try:
                view = OrganizerProcessingActionView()
                view.request = request
                response = view.post(request, submission_id=submission_id, action=action)
                if response.status_code >= 400:
                    failed.append({"id": submission_id, "error": "failed"})
                else:
                    processed.append(submission_id)
            except Exception:
                failed.append({"id": submission_id, "error": "failed"})
        rid = problems.request_id(request)
        return Response({"data": {"processed": processed, "failed": failed, "comment": comment}, "meta": {"requestId": rid}})


class OrganizerProcessingExportView(_StaffView):
    def get(self, request: Request) -> Response:
        export_type = (request.query_params.get("type") or "applications").strip()
        submissions = SubmissionModel.objects.filter(deleted_at__isnull=True).order_by("-updated_at")
        buffer = StringIO()
        writer = csv.writer(buffer)
        if export_type == "teachers":
            writer.writerow(["submission_id", "teacher_name", "role"])
            for model in submissions:
                for teacher in model.teachers or []:
                    writer.writerow(
                        [
                            str(model.id),
                            " ".join(
                                filter(None, [str(teacher.get("last_name") or ""), str(teacher.get("first_name") or "")])
                            ).strip(),
                            str(teacher.get("role") or ""),
                        ]
                    )
        elif export_type == "organizations":
            writer.writerow(["submission_id", "organization"])
            apps = ApplicationModel.objects.filter(deleted_at__isnull=True).values("organization_name", "submission_refs")
            for row in apps:
                for ref in row.get("submission_refs") or []:
                    writer.writerow([str(ref.get("submission_id") or ""), str(row.get("organization_name") or "")])
        else:
            writer.writerow(["submission_id", "competition_id", "applicant_id", "status", "created_at", "updated_at"])
            for model in submissions:
                writer.writerow([model.id, model.competition_id, model.applicant_id, model.status, model.created_at, model.updated_at])

        content = buffer.getvalue()
        response = Response(content, content_type="text/csv; charset=utf-8")
        filename = f"{export_type}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
