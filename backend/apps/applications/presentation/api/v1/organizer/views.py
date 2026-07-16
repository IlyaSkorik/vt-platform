from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
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
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.identity.infrastructure.models.user import UserModel
from apps.organization.presentation.permissions import IsOrganizationStaff

_QUEUE_BY_STATUS = {
    "SUBMITTED": "NEW",
    "UNDER_REVIEW": "NEW",
    "REQUIRES_CORRECTION": "NEW",
    "APPROVED": "READY",
    "WAITING_PAYMENT": "READY",
    "PAID": "READY",
    "ACCEPTED": "READY",
    "SCHEDULED": "RUNNING",
    "COMPLETED": "COMPLETED",
    "CANCELLED": "ARCHIVE",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _application_meta_for_submission(submission_id: str) -> tuple[str | None, str | None, str | None]:
    app_rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values(
        "id", "submission_refs", "payment_receipt", "competition_id"
    )
    for row in app_rows:
        refs = row.get("submission_refs") or []
        if any(str(ref.get("submission_id") or "") == submission_id for ref in refs):
            receipt = row.get("payment_receipt") or {}
            return (
                str(row.get("id") or "") or None,
                str(receipt.get("file_reference") or "").strip() or None,
                str(row.get("competition_id") or "") or None,
            )
    return None, None, None


def _capabilities(status: str) -> list[dict[str, str]]:
    mapping: dict[str, list[tuple[str, str]]] = {
        "SUBMITTED": [("approve", "Одобрить"), ("return_for_correction", "Вернуть на исправление"), ("cancel", "Отменить")],
        "UNDER_REVIEW": [("approve", "Одобрить"), ("return_for_correction", "Вернуть на исправление"), ("cancel", "Отменить")],
        "REQUIRES_CORRECTION": [],
        "APPROVED": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
        "WAITING_PAYMENT": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
        "PAID": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
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
        competition_ids = [row["id"] for row in competitions]
        competition_name = {str(row["id"]): row["title"] for row in competitions}
        nomination_name = {
            str(row["id"]): str(row["name"])
            for row in CategoryModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
        }
        discipline_name = {
            str(row["id"]): str(row["name"])
            for row in DisciplineModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
        }
        age_category_name = {
            str(row["id"]): str(row["name"])
            for row in AgeCategoryModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
        }
        participant_group_name = {
            str(row["id"]): str(row["name"])
            for row in ParticipantGroupModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
        }
        participation_format_name = {
            str(row["id"]): str(row["name"])
            for row in ParticipationFormatModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values(
                "id", "name"
            )
        }
        organization_by_submission: dict[str, str] = {}
        application_by_submission: dict[str, str] = {}
        application_meta_by_id: dict[str, dict[str, str | None]] = {}
        submission_ids_by_application: dict[str, list[str]] = {}
        application_rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values(
            "id", "organization_name", "submission_refs", "payment_receipt", "total_price"
        )
        for row in application_rows:
            application_id = str(row.get("id"))
            organization_name = str(row.get("organization_name") or "")
            payment_receipt = row.get("payment_receipt") or {}
            receipt_ref = str(payment_receipt.get("file_reference") or "").strip()
            total_price = row.get("total_price") or {}
            application_meta_by_id[application_id] = {
                "receipt_ref": receipt_ref or None,
                "total_amount": str(total_price.get("amount") or "").strip() or None,
                "total_currency": str(total_price.get("currency") or "").strip() or None,
            }
            refs = row.get("submission_refs") or []
            submission_ids_by_application[application_id] = [
                str(ref.get("submission_id") or "") for ref in refs if str(ref.get("submission_id") or "")
            ]
            for ref in refs:
                submission_id = str(ref.get("submission_id") or "")
                if submission_id:
                    application_by_submission[submission_id] = application_id
                    organization_by_submission[submission_id] = organization_name

        submissions = list(
            SubmissionModel.objects.filter(
                deleted_at__isnull=True,
                competition_id__in=[row["id"] for row in competitions],
                status__in=list(_QUEUE_BY_STATUS),
            ).order_by("-updated_at")
        )
        submission_model_by_id = {str(model.id): model for model in submissions}

        all_rows: list[dict[str, Any]] = []
        rows: list[dict[str, Any]] = []
        for model in submissions:
            performance = model.performance or {}
            participants = model.participants or []
            teachers = model.teachers or []
            missing_requests = model.missing_files_requests or []
            has_missing_files = any(not bool(entry.get("resolved_at")) for entry in missing_requests)
            queue_key = _QUEUE_BY_STATUS.get(model.status, "ARCHIVE")
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
            application_id = application_by_submission.get(str(model.id), "")
            app_meta = application_meta_by_id.get(application_id or "", {})
            receipt_ref = str(app_meta.get("receipt_ref") or "")
            payment = "RECEIPT_ATTACHED" if receipt_ref else "RECEIPT_MISSING"
            has_corrections = model.status == "REQUIRES_CORRECTION"
            if model.status not in {"REQUIRES_CORRECTION", "SCHEDULED", "COMPLETED", "CANCELLED"}:
                queue_key = "READY" if receipt_ref else "WAITING_PAYMENT"
            row = {
                "id": str(model.id),
                "applicationId": application_id or None,
                "applicationNumber": (application_id or str(model.id))[:8].upper(),
                "competitionId": str(model.competition_id),
                "competition": competition_name.get(str(model.competition_id), "—"),
                "applicant": applicant,
                "performancesCount": 1,
                "participantsCount": sum(int(item.get("member_count", 1)) for item in participants),
                "status": model.status,
                "queue": queue_key,
                "paymentStatus": payment,
                "hasReceipt": bool(receipt_ref),
                "receiptFileReference": receipt_ref or None,
                "organization": organization_name or None,
                "submissionDate": model.created_at,
                "lastActivity": model.updated_at,
                "badges": {
                    "hasCorrections": has_corrections,
                    "hasMissingFiles": has_missing_files,
                },
                "capabilities": _capabilities(model.status),
            }
            all_rows.append(row)

            if query and query not in haystack:
                continue
            if queue_filter and queue_key != queue_filter:
                continue
            if competition_filter and str(model.competition_id) != competition_filter:
                continue
            if status_filter and model.status != status_filter:
                continue
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
            if has_corrections_filter in {"true", "false"} and has_corrections != (has_corrections_filter == "true"):
                continue
            if has_missing_files_filter in {"true", "false"} and has_missing_files != (has_missing_files_filter == "true"):
                continue
            rows.append(row)

        queue_source = (
            [item for item in all_rows if item.get("competitionId") == competition_filter]
            if competition_filter
            else all_rows
        )
        queue_counts = Counter(item["queue"] for item in queue_source)
        selected = next((item for item in rows if item["id"] == selected_id), rows[0] if rows else None)
        detail: dict[str, Any] | None = None
        if selected is not None:
            try:
                selected_submission_id = selected["id"]
                selected_application_id = application_by_submission.get(selected_submission_id)
                related_submission_ids = (
                    submission_ids_by_application.get(selected_application_id or "", [selected_submission_id])
                    if selected_application_id
                    else [selected_submission_id]
                )
                related_submission_ids = [sid for sid in related_submission_ids if sid in submission_model_by_id]
                if not related_submission_ids:
                    related_submission_ids = [selected_submission_id]
                related_dtos = [
                    composition.build_get_submission_handler().handle(
                        GetSubmissionQuery(submission_id=submission_id, requested_by=user_id)
                    )
                    for submission_id in related_submission_ids
                ]
            except ApplicationError:
                detail = None
            else:
                representative = related_dtos[0]
                participants = [
                    {"id": p.id, "name": p.display_name, "memberCount": p.member_count}
                    for dto in related_dtos
                    for p in dto.participants
                ]
                teachers = [
                    {"id": t.id, "name": f"{t.last_name} {t.first_name}", "role": t.role}
                    for dto in related_dtos
                    for t in dto.teachers
                ]
                attachments = [
                    {"id": a.id, "type": a.type, "fileReference": a.file_reference}
                    for dto in related_dtos
                    for a in dto.attachments
                ]
                total_amount_value = application_meta_by_id.get(selected_application_id or "", {}).get("total_amount")
                total_currency_value = application_meta_by_id.get(selected_application_id or "", {}).get("total_currency")
                if not total_amount_value:
                    total_dec = Decimal("0")
                    fallback_currency: str | None = None
                    for dto in related_dtos:
                        if dto.price is None:
                            continue
                        try:
                            total_dec += Decimal(str(dto.price.amount))
                        except (InvalidOperation, ValueError):
                            continue
                        fallback_currency = dto.price.currency
                    if total_dec > 0:
                        total_amount_value = format(total_dec, "f")
                        total_currency_value = fallback_currency or "BYN"
                timeline = [
                    {
                        "kind": "transition",
                        "label": f"[{dto.id[:8].upper()}] {from_status or 'NONE'} -> {to_status}",
                        "at": occurred_at,
                    }
                    for dto in related_dtos
                    for from_status, to_status, occurred_at in dto.status_history
                ]
                timeline.extend(
                    {
                        "kind": "review",
                        "label": f"[{dto.id[:8].upper()}] {review.comment}",
                        "at": review.created_at,
                    }
                    for dto in related_dtos
                    for review in dto.reviews
                )
                timeline.extend(
                    {
                        "kind": "missing_files",
                        "label": f"[{submission_id[:8].upper()}] Запрошены файлы: {', '.join(entry.get('types', []))}",
                        "at": entry.get("created_at"),
                    }
                    for submission_id in related_submission_ids
                    for entry in (submission_model_by_id[submission_id].missing_files_requests or [])
                )
                timeline.sort(key=lambda entry: str(entry.get("at") or ""), reverse=True)
                audit = [
                    {
                        "at": review.created_at,
                        "by": review.reviewer_id,
                        "reason": f"[{dto.id[:8].upper()}] {review.comment}",
                    }
                    for dto in related_dtos
                    for review in dto.reviews
                ]
                detail = {
                    "id": representative.id,
                    "status": representative.status,
                    "performance": representative.performance.title if representative.performance else None,
                    "performances": [
                        {
                            "submissionId": dto.id,
                            "title": dto.performance.title if dto.performance else "Без названия номера",
                            "status": dto.status,
                            "nominationName": nomination_name.get(dto.performance.nomination_id, dto.performance.nomination_id)
                            if dto.performance
                            else None,
                            "disciplineName": discipline_name.get(dto.performance.discipline_id, dto.performance.discipline_id)
                            if dto.performance
                            else None,
                            "ageCategoryName": age_category_name.get(dto.performance.age_category_id, dto.performance.age_category_id)
                            if dto.performance
                            else None,
                            "participantGroupName": participant_group_name.get(
                                dto.performance.participant_group_id, dto.performance.participant_group_id
                            )
                            if dto.performance
                            else None,
                            "participationFormatName": participation_format_name.get(
                                dto.performance.participation_format_id, dto.performance.participation_format_id
                            )
                            if dto.performance
                            else None,
                            "durationSeconds": dto.performance.duration_seconds if dto.performance else None,
                            "participantsCount": len(dto.participants),
                            "teachersCount": len(dto.teachers),
                            "participants": [
                                {"id": p.id, "name": p.display_name, "memberCount": p.member_count} for p in dto.participants
                            ],
                            "teachers": [
                                {"id": t.id, "name": f"{t.last_name} {t.first_name}", "role": t.role} for t in dto.teachers
                            ],
                            "priceAmount": dto.price.amount if dto.price else None,
                            "priceCurrency": dto.price.currency if dto.price else None,
                            "attachments": [
                                {"id": a.id, "type": a.type, "fileReference": a.file_reference} for a in dto.attachments
                            ],
                        }
                        for dto in related_dtos
                    ],
                    "participants": participants,
                    "teachers": teachers,
                    "attachments": attachments,
                    "price": representative.price.amount if representative.price else None,
                    "totalPriceAmount": total_amount_value,
                    "totalPriceCurrency": total_currency_value,
                    "receiptFileReference": application_meta_by_id.get(selected_application_id or "", {}).get("receipt_ref"),
                    "timeline": timeline,
                    "audit": audit,
                    "internalNotes": [
                        note
                        for submission_id in related_submission_ids
                        for note in (submission_model_by_id[submission_id].organizer_notes or [])
                    ],
                    "participantMessages": [
                        message
                        for submission_id in related_submission_ids
                        for message in (submission_model_by_id[submission_id].participant_messages or [])
                    ],
                }

        payload = {
            "queues": [
                {"key": "NEW", "label": "На доработке", "count": queue_counts.get("NEW", 0)},
                {"key": "WAITING_PAYMENT", "label": "Ожидают оплату", "count": queue_counts.get("WAITING_PAYMENT", 0)},
                {"key": "READY", "label": "Готовы к конкурсу", "count": queue_counts.get("READY", 0)},
                {"key": "RUNNING", "label": "Назначены в конкурс", "count": queue_counts.get("RUNNING", 0)},
                {"key": "COMPLETED", "label": "Завершены", "count": queue_counts.get("COMPLETED", 0)},
                {"key": "ARCHIVE", "label": "Отменены", "count": queue_counts.get("ARCHIVE", 0)},
            ],
            "metrics": {
                "needReview": queue_counts.get("NEW", 0),
                "needCorrection": 0,
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
                if not comment:
                    return Response({"detail": "Укажите комментарий для участника перед возвратом на исправление."}, status=400)
                result = composition.build_return_for_correction_handler().handle(
                    ReturnSubmissionForCorrectionCommand(
                        submission_id=submission_id,
                        reviewer_id=user_id,
                        comment=comment,
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
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                if model.status in {"APPROVED", "WAITING_PAYMENT"}:
                    _, receipt_ref, _ = _application_meta_for_submission(submission_id)
                    has_receipt = bool(receipt_ref)
                    if not has_receipt:
                        return Response({"detail": "Для подтверждения участия нужно прикрепить квитанцию."}, status=400)
                    if model.status == "APPROVED":
                        composition.build_mark_waiting_payment_handler().handle(
                            MarkWaitingPaymentCommand(submission_id=submission_id, reviewer_id=user_id)
                        )
                    composition.build_mark_paid_handler().handle(
                        MarkPaidCommand(submission_id=submission_id, reviewer_id=user_id)
                    )
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
                if not comment:
                    return Response({"detail": "Добавьте комментарий для участника к запросу недостающих файлов."}, status=400)
                if not missing_types:
                    return Response({"detail": "Укажите хотя бы один тип недостающего файла."}, status=400)
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                requests = list(model.missing_files_requests or [])
                requests.append(
                    {
                        "id": f"mf-{len(requests) + 1}",
                        "types": [str(item).upper() for item in missing_types],
                        "message": comment,
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
                if not comment:
                    return Response({"detail": "Введите текст внутренней заметки."}, status=400)
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
                if not comment:
                    return Response({"detail": "Введите текст сообщения участнику."}, status=400)
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                messages = list(model.participant_messages or [])
                messages.append({"text": comment, "created_by": user_id, "created_at": _now().isoformat()})
                model.participant_messages = messages
                model.updated_at = _now()
                model.save(update_fields=["participant_messages", "updated_at"])
                body = {"id": submission_id, "status": model.status, "capabilities": _capabilities(model.status)}
                rid = problems.request_id(request)
                return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})
            elif action == "send_payment_reminder":
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                if model.status in {"COMPLETED", "CANCELLED", "SCHEDULED"}:
                    return Response({"detail": "Напоминание об оплате доступно только для активных заявок."}, status=400)
                application_id, receipt_ref, competition_id = _application_meta_for_submission(submission_id)
                if receipt_ref:
                    return Response({"detail": "Квитанция уже прикреплена, напоминание не требуется."}, status=400)
                recipient = UserModel.objects.filter(id=model.applicant_id, deleted_at__isnull=True).first()
                if recipient is None:
                    return Response({"detail": "Не найден получатель напоминания."}, status=400)
                competition_title = (
                    CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first()
                    if competition_id
                    else None
                )
                application_number = (application_id or submission_id)[:8].upper()
                subject = f"Напоминание об оплате заявки #{application_number}"
                body_text = (
                    f"Здравствуйте, {recipient.first_name}!\n\n"
                    f"Пожалуйста, прикрепите квитанцию об оплате по заявке #{application_number}"
                    f"{f' ({competition_title})' if competition_title else ''}.\n"
                    "После прикрепления квитанции заявка будет готова к дальнейшей обработке.\n\n"
                    "С уважением,\nОргкомитет конкурса"
                )
                send_mail(
                    subject=subject,
                    message=body_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
                messages = list(model.participant_messages or [])
                messages.append(
                    {
                        "text": f"Отправлено напоминание об оплате на {recipient.email}",
                        "created_by": user_id,
                        "created_at": _now().isoformat(),
                    }
                )
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
