from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import PurePosixPath
from typing import Any

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.application.dto import TeacherView
from apps.applications.application.dto.commands import (
    AcceptSubmissionCommand,
    ApproveSubmissionCommand,
    CancelSubmissionByReviewerCommand,
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
from apps.applications.presentation.api.v1.files import file_url
from apps.applications.presentation.api.v1.mail import queue_review_email
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
from apps.identity.infrastructure.auth import CredentialAwareJWTAuthentication
from apps.identity.infrastructure.models.user import UserModel
from apps.notifications.infrastructure import feed as notification_feed
from apps.notifications.infrastructure.models import NotificationKind
from apps.organization.domain.value_objects import OrganizationModule
from apps.organization.presentation.permissions import IsModuleEnabled, IsOrganizationStaff
from apps.organization.presentation.scope import callers_organization_id, is_platform_operator
from apps.teachers.infrastructure.models import TeacherModel
from config.archive import ArchiveMember, zip_response

_QUEUE_BY_STATUS = {
    "SUBMITTED": "NEW",
    "UNDER_REVIEW": "NEW",
    "REQUIRES_CORRECTION": "NEW",
    "APPROVED": "READY",
    "WAITING_PAYMENT": "READY",
    "PAID": "READY",
    "ACCEPTED": "READY",
    "SCHEDULED": "RUNNING",
    "COMPLETED": "RUNNING",
    "CANCELLED": "ARCHIVE",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _directory_phones(teachers: Sequence[TeacherView]) -> dict[str, str]:
    """Телефоны педагогов заявки — одним запросом в справочник кабинета.

    На заявке от педагога лежат только имя, роль и ссылка на карточку в справочнике;
    телефон живёт там. Организатору он нужен ровно тогда, когда с номером что-то не
    так и звонить надо не участнику, а тому, кто его готовил, — поэтому читается
    вместе с карточкой, а не отдельным запросом по клику.

    Педагог, вписанный руками (без ссылки на справочник), сюда не попадает: звонить
    некуда, и это честнее пустой строки.
    """
    directory_ids = {teacher.directory_teacher_id for teacher in teachers if teacher.directory_teacher_id}
    if not directory_ids:
        return {}
    rows = TeacherModel.objects.filter(pk__in=directory_ids, deleted_at__isnull=True).values_list("id", "phone")
    return {str(directory_id): cleaned for directory_id, phone in rows if (cleaned := (phone or "").strip())}


def _teacher_card(teacher: TeacherView, phones: Mapping[str, str]) -> dict[str, Any]:
    """Педагог так, как его читает организатор: имя, роль и телефон, если он есть."""
    directory_id = teacher.directory_teacher_id
    return {
        "id": teacher.id,
        "name": f"{teacher.last_name} {teacher.first_name}",
        "role": teacher.role,
        "phone": phones.get(directory_id) if directory_id else None,
    }


def _visible_competitions(request: Request) -> Any:
    """The competitions this caller's organization runs (all of them, for the operator).

    Everything in the organizer workspace hangs off this queryset — the queues, the
    filters, the exports, the archives — so scoping it here scopes the workspace.
    A caller who is staff of no organization sees nothing rather than everything.
    """
    competitions = CompetitionModel.objects.filter(deleted_at__isnull=True)
    if is_platform_operator(request):
        return competitions
    organization_id = callers_organization_id(request)
    if organization_id is None:
        return competitions.none()
    return competitions.filter(organizer_id=organization_id)


def _receipt_references(payment_receipts: Any) -> list[str]:
    """The stored file of every receipt on an order, oldest first, blanks dropped.

    An order carries a list because its fee is regularly settled by more than one
    transfer; everything downstream (the payment badge, the archive, the reminder)
    asks about the whole list rather than a single document.
    """
    return [reference for entry in payment_receipts or [] if (reference := str((entry or {}).get("file_reference") or "").strip())]


def _payer_full_name(row: Any) -> str | None:
    """The order's payer rendered ``Last First Middle``, or ``None`` if unnamed.

    Only festivals that ask for the contract party have anything in these columns, so
    an absent name is the normal case rather than missing data.
    """
    parts = [str(row.get(key) or "").strip() for key in ("payer_last_name", "payer_first_name", "payer_middle_name")]
    named = [part for part in parts if part]
    return " ".join(named) or None


def _educational_organization_name(row: Any) -> str | None:
    """Учреждение, от которого пришла заявка, — снимок имени на момент выбора.

    Организатор разбирает очередь по учреждениям: одна школа присылает десяток
    номеров, и звонить, сверять оплату и собирать программу удобнее по ней, а не по
    каждому участнику отдельно. Читается снимок с самой заявки, а не справочник
    кабинета: учреждение там могли с тех пор переименовать или удалить, а в заявке
    оно должно остаться таким, каким его выбирали.

    Заявку можно подать и не от учреждения — тогда поля просто нет, и строка на
    карточке не рисуется.
    """
    return str(row.get("organization_name") or "").strip() or None


def _participant_label(entry: Any) -> str:
    """One performer as the organizer knows them — a soloist's name or the group's.

    A collective stores only ``display_name``; a soloist stores the name parts and,
    often, a ``display_name`` repeating them. Reading the parts first keeps the
    order ``Last First Middle`` even when the stored caption was typed the other
    way round.
    """
    person = " ".join(part for key in ("last_name", "first_name", "middle_name") if (part := str(entry.get(key) or "").strip()))
    return person or str(entry.get("display_name") or "").strip()


def _applicant_label(participants: Sequence[Any], *fallbacks: str | None) -> str:
    """Who the entry is for, in one line for the queue card.

    The queue used to print ``applicant_id`` — a raw UUID that tells the organizer
    nothing and cannot be matched against a transfer or a phone call. The performers
    are what they recognise, so the card names the first one and counts the rest;
    only an entry with no performers at all falls back to the studio or the payer.
    """
    names = [label for entry in participants or [] if (label := _participant_label(entry))]
    if names:
        return names[0] if len(names) == 1 else f"{names[0]} и ещё {len(names) - 1}"
    for fallback in fallbacks:
        if fallback and fallback.strip():
            return fallback.strip()
    return "—"


def _duration_seconds(value: Any) -> int:
    """Хронометраж номера в секундах; всё, что не число, считается нулём.

    Длительности складывают в итог по жанру, и одна заявка с испорченным значением
    не должна обнулять или взорвать весь подсчёт.
    """
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _receipt_urls(references: Sequence[str]) -> list[str]:
    """The same receipts as addresses a browser can open.

    A stored reference is an opaque storage key, and the organizer console turns one
    into a link. Prefixing ``/media/`` on the client used to be enough because the
    filesystem happened to serve exactly that; with the files in a bucket that link
    points at the API host, where nothing of the sort exists, and every "Открыть
    квитанцию" answers 404. Asking the storage (``file_url``) is what the submission
    attachments beside them already do.
    """
    return [url for reference in references if (url := file_url(reference))]


def _application_meta_for_submission(submission_id: str) -> tuple[str | None, list[str], str | None]:
    app_rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values("id", "submission_refs", "payment_receipts", "competition_id")
    for row in app_rows:
        refs = row.get("submission_refs") or []
        if any(str(ref.get("submission_id") or "") == submission_id for ref in refs):
            return (
                str(row.get("id") or "") or None,
                _receipt_references(row.get("payment_receipts")),
                str(row.get("competition_id") or "") or None,
            )
    return None, [], None


def _submission_ids_for_application(application_id: str | None) -> list[str]:
    if not application_id:
        return []
    row = ApplicationModel.objects.filter(id=application_id, deleted_at__isnull=True).values("submission_refs").first()
    if not row:
        return []
    refs = row.get("submission_refs") or []
    return [str(ref.get("submission_id") or "").strip() for ref in refs if str(ref.get("submission_id") or "").strip()]


def _application_urls(application_id: str | None) -> tuple[str, str]:
    base = str(getattr(settings, "FRONTEND_BASE_URL", "") or "").rstrip("/")
    cabinet_url = f"{base}/cabinet/applications" if base else "/cabinet/applications"
    if application_id:
        return cabinet_url, f"{cabinet_url}/{application_id}"
    return cabinet_url, cabinet_url


def _cabinet_path(application_id: str | None) -> str:
    """The same destination as the letter's button, as a path.

    A feed entry is read inside the cabinet that already knows its own origin, so it
    stores where to go rather than which host to go to — the row then renders
    correctly whatever `FRONTEND_BASE_URL` was when it was written.
    """
    return f"/cabinet/applications/{application_id}" if application_id else "/cabinet/applications"


def _missing_type_label(raw: str) -> str:
    labels = {
        "MUSIC": "Музыка",
        "VIDEO": "Видео",
        "DOCUMENT": "Документы",
        "RECEIPT": "Квитанция",
        "OTHER": "Другое",
    }
    key = str(raw or "").upper()
    return labels.get(key, key)


def _capabilities(status: str) -> list[dict[str, str]]:
    """What the organizer may do to a submission in this status.

    Cancellation stays on offer once the entry is in the running order (``ACCEPTED``,
    ``SCHEDULED``): the applicant can no longer withdraw there, but the organizer
    decides such a withdrawal case by case — a disqualification, a no-show, or a
    request granted as an exception. ``COMPLETED`` offers nothing: the performance
    took place.
    """
    mapping: dict[str, list[tuple[str, str]]] = {
        "SUBMITTED": [("approve", "Одобрить"), ("return_for_correction", "Вернуть на исправление"), ("cancel", "Отменить")],
        "UNDER_REVIEW": [("approve", "Одобрить"), ("return_for_correction", "Вернуть на исправление"), ("cancel", "Отменить")],
        "REQUIRES_CORRECTION": [],
        "APPROVED": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
        "WAITING_PAYMENT": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
        "PAID": [("confirm_participation", "Подтвердить участие"), ("cancel", "Отменить")],
        "ACCEPTED": [("move_to_running", "Перевести на фестиваль"), ("cancel", "Отменить")],
        "SCHEDULED": [("cancel", "Отменить")],
        "COMPLETED": [],
        "CANCELLED": [],
    }
    return [{"key": key, "label": label} for key, label in mapping.get(status, [])]


class _StaffView(APIView):
    authentication_classes = (CredentialAwareJWTAuthentication,)
    permission_classes = (IsAuthenticated, IsOrganizationStaff, IsModuleEnabled.of(OrganizationModule.APPLICATIONS))


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
        # Жанр фильтруется по названию, а не по id: у каждого фестиваля своя строка
        # справочника, и организатор, выбирая «Вокал», имеет в виду вокал везде.
        nomination_filter = (request.query_params.get("nomination") or "").strip().lower()
        organization_filter = (request.query_params.get("organization") or "").strip().lower()
        from_date = (request.query_params.get("from") or "").strip()
        to_date = (request.query_params.get("to") or "").strip()
        has_corrections_filter = (request.query_params.get("hasCorrections") or "").strip().lower()
        has_missing_files_filter = (request.query_params.get("hasMissingFiles") or "").strip().lower()

        competitions = list(_visible_competitions(request).values("id", "title", "status").order_by("title"))
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
            for row in ParticipationFormatModel.objects.filter(deleted_at__isnull=True, competition_id__in=competition_ids).values("id", "name")
        }
        organization_by_submission: dict[str, str] = {}
        application_by_submission: dict[str, str] = {}
        application_meta_by_id: dict[str, dict[str, Any]] = {}
        submission_ids_by_application: dict[str, list[str]] = {}
        application_rows = ApplicationModel.objects.filter(deleted_at__isnull=True).values(
            "id",
            "organization_name",
            "payer_last_name",
            "payer_first_name",
            "payer_middle_name",
            "submission_refs",
            "payment_receipts",
            "total_price",
        )
        for row in application_rows:
            application_id = str(row.get("id"))
            organization_name = str(row.get("organization_name") or "")
            receipt_refs = _receipt_references(row.get("payment_receipts"))
            total_price = row.get("total_price") or {}
            application_meta_by_id[application_id] = {
                "receipt_refs": receipt_refs,
                # Who the contract is made out to. Only festivals that collect it have
                # anything here, so the card renders the block conditionally.
                "payer_name": _payer_full_name(row),
                # Учреждение, от которого пришла заявка; у частной подачи его нет.
                "organization_name": _educational_organization_name(row),
                # The snapshot's grand total lives under "total" (see ApplicationMapper);
                # "amount" is the single-Money key, accepted so an older row still reads.
                "total_amount": str(total_price.get("total") or total_price.get("amount") or "").strip() or None,
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
            nomination_id = str(performance.get("nomination_id") or "")
            nomination = nomination_name.get(nomination_id, "")
            duration_seconds = _duration_seconds(performance.get("duration_seconds"))
            applicant_id = str(model.applicant_id)
            organization_name = organization_by_submission.get(str(model.id), "")
            teachers_text = " ".join(
                " ".join(filter(None, [str(item.get("last_name") or ""), str(item.get("first_name") or "")])).strip() for item in teachers
            )
            application_id = application_by_submission.get(str(model.id), "")
            applicant = _applicant_label(
                participants,
                organization_name,
                application_meta_by_id.get(application_id or "", {}).get("payer_name"),
            )
            # The order number is what the organizer sees on the card and what every
            # letter about the order quotes, so it has to be what they can paste back
            # into the search box.
            application_number = (application_id or str(model.id))[:8].upper()
            haystack = " ".join(
                [
                    str(model.id),
                    application_id,
                    application_number,
                    title,
                    applicant,
                    applicant_id,
                    nomination,
                    competition_name.get(str(model.competition_id), ""),
                    organization_name,
                    teachers_text,
                ]
            ).lower()
            app_meta = application_meta_by_id.get(application_id or "", {})
            receipt_refs = list(app_meta.get("receipt_refs") or [])
            payment = "RECEIPT_ATTACHED" if receipt_refs else "RECEIPT_MISSING"
            has_corrections = model.status == "REQUIRES_CORRECTION"
            if model.status not in {"REQUIRES_CORRECTION", "SCHEDULED", "COMPLETED", "CANCELLED"}:
                queue_key = "READY" if receipt_refs else "WAITING_PAYMENT"
            # Named `card`, not `row`: `row` is already the loop variable for the
            # `.values()` querysets above, and reusing it made the checker treat this
            # response payload as one of those database row shapes.
            card: dict[str, Any] = {
                "id": str(model.id),
                "applicationId": application_id or None,
                "applicationNumber": application_number,
                "competitionId": str(model.competition_id),
                "competition": competition_name.get(str(model.competition_id), "—"),
                "applicant": applicant,
                "nomination": nomination or None,
                "durationSeconds": duration_seconds,
                "performancesCount": 1,
                "participantsCount": sum(int(item.get("member_count", 1)) for item in participants),
                "status": model.status,
                "queue": queue_key,
                "paymentStatus": payment,
                "hasReceipt": bool(receipt_refs),
                "receiptFileReferences": _receipt_urls(receipt_refs),
                "organization": organization_name or None,
                "submissionDate": model.created_at,
                "lastActivity": model.updated_at,
                "badges": {
                    "hasCorrections": has_corrections,
                    "hasMissingFiles": has_missing_files,
                },
                "capabilities": _capabilities(model.status),
            }
            all_rows.append(card)

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
            if nomination_filter and nomination.lower() != nomination_filter:
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
            rows.append(card)

        queue_source = [item for item in all_rows if item.get("competitionId") == competition_filter] if competition_filter else all_rows
        # Список жанров собран из самих заявок, а не из справочника: пункт, по которому
        # ничего не найдётся, в фильтре только мешает. Фестивальный фильтр сужает и его.
        nomination_options = sorted({name for item in queue_source if (name := str(item.get("nomination") or ""))})
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
                    composition.build_get_submission_handler().handle(GetSubmissionQuery(submission_id=submission_id, requested_by=user_id))
                    for submission_id in related_submission_ids
                ]
            except ApplicationError:
                detail = None
            else:
                representative = related_dtos[0]
                participants = [{"id": p.id, "name": p.display_name, "memberCount": p.member_count} for dto in related_dtos for p in dto.participants]
                teacher_views = [t for dto in related_dtos for t in dto.teachers]
                teacher_phones = _directory_phones(teacher_views)
                teachers = [_teacher_card(t, teacher_phones) for t in teacher_views]
                attachments = [
                    {"id": a.id, "type": a.type, "fileReference": file_url(a.file_reference)} for dto in related_dtos for a in dto.attachments
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
                            # The applicant's optional note for the organizers; blank when unset.
                            "comment": (dto.performance.comment or None) if dto.performance else None,
                            # What ages the performers are, in the applicant's words. Only a
                            # mixed age category asks for it, so it is usually blank.
                            "ageComposition": (dto.performance.age_composition or None) if dto.performance else None,
                            "participantsCount": len(dto.participants),
                            "teachersCount": len(dto.teachers),
                            "participants": [{"id": p.id, "name": p.display_name, "memberCount": p.member_count} for p in dto.participants],
                            "teachers": [_teacher_card(t, teacher_phones) for t in dto.teachers],
                            "priceAmount": dto.price.amount if dto.price else None,
                            "priceCurrency": dto.price.currency if dto.price else None,
                            "attachments": [{"id": a.id, "type": a.type, "fileReference": file_url(a.file_reference)} for a in dto.attachments],
                        }
                        for dto in related_dtos
                    ],
                    "participants": participants,
                    "teachers": teachers,
                    "attachments": attachments,
                    "price": representative.price.amount if representative.price else None,
                    "totalPriceAmount": total_amount_value,
                    "totalPriceCurrency": total_currency_value,
                    "receiptFileReferences": _receipt_urls(application_meta_by_id.get(selected_application_id or "", {}).get("receipt_refs") or []),
                    "educationalOrganization": application_meta_by_id.get(selected_application_id or "", {}).get("organization_name"),
                    "payerName": application_meta_by_id.get(selected_application_id or "", {}).get("payer_name"),
                    "timeline": timeline,
                    "audit": audit,
                    "internalNotes": [
                        note for submission_id in related_submission_ids for note in (submission_model_by_id[submission_id].organizer_notes or [])
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
                {"key": "READY", "label": "Готовы к фестивалю", "count": queue_counts.get("READY", 0)},
                {"key": "RUNNING", "label": "Назначены на фестиваль", "count": queue_counts.get("RUNNING", 0)},
                {"key": "ARCHIVE", "label": "Отменены", "count": queue_counts.get("ARCHIVE", 0)},
            ],
            "metrics": {
                "needReview": queue_counts.get("NEW", 0),
                "needCorrection": 0,
                "needPayment": queue_counts.get("WAITING_PAYMENT", 0),
                "ready": queue_counts.get("READY", 0),
                "running": queue_counts.get("RUNNING", 0),
                "completed": 0,
            },
            "competitions": [{"id": str(row["id"]), "title": row["title"], "status": row["status"]} for row in competitions],
            "nominations": nomination_options,
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
                result = composition.build_start_review_handler().handle(StartReviewCommand(submission_id=submission_id, reviewer_id=user_id))
            elif action == "approve":
                application_id, _, competition_id = _application_meta_for_submission(submission_id)
                target_submission_ids = _submission_ids_for_application(application_id) or [submission_id]
                processed_ids: list[str] = []
                result = None
                for target_id in target_submission_ids:
                    model = SubmissionModel.objects.get(id=target_id, deleted_at__isnull=True)
                    if model.status not in {"SUBMITTED", "UNDER_REVIEW"}:
                        continue
                    if model.status == "SUBMITTED":
                        composition.build_start_review_handler().handle(StartReviewCommand(submission_id=target_id, reviewer_id=user_id))
                    # Approval takes the submission straight into the running competition
                    # (UNDER_REVIEW → APPROVED → … → ACCEPTED → SCHEDULED) — no separate
                    # "confirm participation" / "move to running" steps for the organizer.
                    composition.build_approve_submission_handler().handle(ApproveSubmissionCommand(submission_id=target_id, reviewer_id=user_id))
                    composition.build_mark_waiting_payment_handler().handle(MarkWaitingPaymentCommand(submission_id=target_id, reviewer_id=user_id))
                    composition.build_mark_paid_handler().handle(MarkPaidCommand(submission_id=target_id, reviewer_id=user_id))
                    composition.build_accept_submission_handler().handle(AcceptSubmissionCommand(submission_id=target_id, reviewer_id=user_id))
                    scheduled = composition.build_schedule_submission_handler().handle(
                        ScheduleSubmissionCommand(submission_id=target_id, reviewer_id=user_id)
                    )
                    if result is None:
                        result = scheduled
                    processed_ids.append(target_id)
                if not processed_ids or result is None:
                    return Response({"detail": "Нет выступлений, доступных для одобрения."}, status=409)
                # An approval is the answer the applicant has been waiting for, and the
                # one outcome they never see by refreshing — the order simply stops
                # being "on review". It is told the same way a return for correction is:
                # a letter, a feed entry, and a line in the order's journal.
                primary_model = SubmissionModel.objects.get(id=processed_ids[0], deleted_at__isnull=True)
                recipient = UserModel.objects.filter(id=primary_model.applicant_id, deleted_at__isnull=True).first()
                if recipient is not None and recipient.email:
                    competition_title = (
                        CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first() if competition_id else None
                    )
                    application_number = (application_id or submission_id)[:8].upper()
                    subject = f"Заявка #{application_number} одобрена организатором"
                    cabinet_url, detail_url = _application_urls(application_id)
                    approved_line = f"Одобрено выступлений: {len(processed_ids)}."
                    body_text = (
                        f"Здравствуйте, {recipient.first_name}!\n\n"
                        f"Организатор одобрил вашу заявку #{application_number}"
                        f"{f' ({competition_title})' if competition_title else ''}.\n"
                        f"{approved_line}\n\n"
                        "Заявка принята к участию — следите за расписанием и сообщениями организатора "
                        "в личном кабинете.\n\n"
                        f"Откройте заявку в личном кабинете: {detail_url}\n"
                        f"Список заявок: {cabinet_url}\n\n"
                        "С уважением,\nОргкомитет фестиваля"
                    )
                    queue_review_email(
                        subject=subject,
                        body=body_text,
                        to=recipient.email,
                        html_body=render_transactional_email_html(
                            title=subject,
                            intro=(
                                f"Организатор одобрил заявку #{application_number}"
                                f"{f' ({competition_title})' if competition_title else ''}. {approved_line}"
                            ),
                            details_label="Что дальше",
                            details="Заявка принята к участию. Расписание и сообщения организатора — в личном кабинете.",
                            button_label="Открыть заявку в ЛК",
                            button_url=detail_url,
                            status="success",
                            status_label="Одобрена",
                        ),
                    )
                    notification_feed.publish(
                        recipient_id=recipient.id,
                        kind=NotificationKind.APPLICATION_APPROVED,
                        title=f"Заявка №{application_number} одобрена",
                        body=f"Организатор одобрил заявку. {approved_line}",
                        link=_cabinet_path(application_id),
                    )
                    for target_id in processed_ids:
                        target_model = SubmissionModel.objects.get(id=target_id, deleted_at__isnull=True)
                        messages = list(target_model.participant_messages or [])
                        messages.append(
                            {
                                "text": f"Email участнику: заявка #{application_number} одобрена организатором ({recipient.email})",
                                "created_by": user_id,
                                "created_at": _now().isoformat(),
                            }
                        )
                        target_model.participant_messages = messages
                        target_model.updated_at = _now()
                        target_model.save(update_fields=["participant_messages", "updated_at"])
            elif action == "return_for_correction":
                if not comment:
                    return Response({"detail": "Укажите комментарий для участника перед возвратом на исправление."}, status=400)
                application_id, _, competition_id = _application_meta_for_submission(submission_id)
                target_submission_ids = _submission_ids_for_application(application_id) or [submission_id]
                # Re-uses the binding annotated in the `approve` branch above — the two
                # branches are mutually exclusive, and re-annotating one name twice in a
                # single scope is what the checker rejects.
                processed_ids = []
                result = None
                for target_id in target_submission_ids:
                    model = SubmissionModel.objects.get(id=target_id, deleted_at__isnull=True)
                    if model.status not in {"SUBMITTED", "UNDER_REVIEW"}:
                        continue
                    if model.status == "SUBMITTED":
                        composition.build_start_review_handler().handle(StartReviewCommand(submission_id=target_id, reviewer_id=user_id))
                    returned = composition.build_return_for_correction_handler().handle(
                        ReturnSubmissionForCorrectionCommand(
                            submission_id=target_id,
                            reviewer_id=user_id,
                            comment=comment,
                        )
                    )
                    if result is None:
                        result = returned
                    processed_ids.append(target_id)
                if not processed_ids or result is None:
                    return Response({"detail": "Нет выступлений, доступных для возврата на исправление."}, status=409)
                primary_model = SubmissionModel.objects.get(id=processed_ids[0], deleted_at__isnull=True)
                recipient = UserModel.objects.filter(id=primary_model.applicant_id, deleted_at__isnull=True).first()
                if recipient is not None and recipient.email:
                    competition_title = (
                        CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first() if competition_id else None
                    )
                    application_number = (application_id or submission_id)[:8].upper()
                    subject = f"Заявка #{application_number} возвращена на исправление"
                    cabinet_url, detail_url = _application_urls(application_id)
                    body_text = (
                        f"Здравствуйте, {recipient.first_name}!\n\n"
                        f"Организатор вернул заявку #{application_number}"
                        f"{f' ({competition_title})' if competition_title else ''} на исправление.\n"
                        f"Возвращено выступлений: {len(processed_ids)}.\n\n"
                        f"Комментарий организатора:\n{comment}\n\n"
                        f"Откройте заявку в личном кабинете: {detail_url}\n"
                        f"Список заявок: {cabinet_url}\n\n"
                        "С уважением,\nОргкомитет фестиваля"
                    )
                    queue_review_email(
                        subject=subject,
                        body=body_text,
                        to=recipient.email,
                        html_body=render_transactional_email_html(
                            title=subject,
                            intro=(
                                f"Организатор вернул заявку #{application_number}"
                                f"{f' ({competition_title})' if competition_title else ''} на исправление."
                                f" Возвращено выступлений: {len(processed_ids)}."
                            ),
                            details_label="Комментарий организатора",
                            details=comment,
                            button_label="Открыть заявку в ЛК",
                            button_url=detail_url,
                            status="warning",
                            status_label="На исправлении",
                        ),
                    )
                    notification_feed.publish(
                        recipient_id=recipient.id,
                        kind=NotificationKind.CORRECTION_REQUESTED,
                        title=f"Заявка №{application_number} возвращена на исправление",
                        body=comment,
                        link=_cabinet_path(application_id),
                    )
                    for target_id in processed_ids:
                        target_model = SubmissionModel.objects.get(id=target_id, deleted_at__isnull=True)
                        messages = list(target_model.participant_messages or [])
                        messages.append(
                            {
                                "text": f"Email участнику: заявка #{application_number} возвращена на исправление ({recipient.email})",
                                "created_by": user_id,
                                "created_at": _now().isoformat(),
                            }
                        )
                        target_model.participant_messages = messages
                        target_model.updated_at = _now()
                        target_model.save(update_fields=["participant_messages", "updated_at"])
            elif action == "request_payment":
                result = composition.build_mark_waiting_payment_handler().handle(
                    MarkWaitingPaymentCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "confirm_payment":
                result = composition.build_mark_paid_handler().handle(MarkPaidCommand(submission_id=submission_id, reviewer_id=user_id))
            elif action == "confirm_participation":
                model = SubmissionModel.objects.get(id=submission_id, deleted_at__isnull=True)
                if model.status in {"APPROVED", "WAITING_PAYMENT"}:
                    _, receipt_refs, _ = _application_meta_for_submission(submission_id)
                    if not receipt_refs:
                        return Response({"detail": "Для подтверждения участия нужно прикрепить квитанцию."}, status=400)
                    if model.status == "APPROVED":
                        composition.build_mark_waiting_payment_handler().handle(
                            MarkWaitingPaymentCommand(submission_id=submission_id, reviewer_id=user_id)
                        )
                    composition.build_mark_paid_handler().handle(MarkPaidCommand(submission_id=submission_id, reviewer_id=user_id))
                result = composition.build_accept_submission_handler().handle(
                    AcceptSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "move_to_running":
                result = composition.build_schedule_submission_handler().handle(
                    ScheduleSubmissionCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "cancel":
                result = composition.build_cancel_submission_by_reviewer_handler().handle(
                    CancelSubmissionByReviewerCommand(submission_id=submission_id, reviewer_id=user_id)
                )
            elif action == "request_missing_files":
                missing_types = request.data.get("types") or []
                if not isinstance(missing_types, list):
                    return Response({"detail": "Список типов документов передан неверно."}, status=400)
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
                recipient = UserModel.objects.filter(id=model.applicant_id, deleted_at__isnull=True).first()
                if recipient is not None and recipient.email:
                    application_id, _, competition_id = _application_meta_for_submission(submission_id)
                    competition_title = (
                        CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first() if competition_id else None
                    )
                    application_number = (application_id or submission_id)[:8].upper()
                    requested_types = ", ".join(_missing_type_label(str(item)) for item in missing_types)
                    subject = f"По заявке #{application_number} запрошены недостающие файлы"
                    cabinet_url, detail_url = _application_urls(application_id)
                    body_text = (
                        f"Здравствуйте, {recipient.first_name}!\n\n"
                        f"Организатор запросил дополнительные файлы по заявке #{application_number}"
                        f"{f' ({competition_title})' if competition_title else ''}.\n"
                        f"Что нужно прикрепить: {requested_types}.\n\n"
                        f"Комментарий организатора:\n{comment}\n\n"
                        f"Откройте заявку в личном кабинете: {detail_url}\n"
                        f"Список заявок: {cabinet_url}\n\n"
                        "С уважением,\nОргкомитет фестиваля"
                    )
                    queue_review_email(
                        subject=subject,
                        body=body_text,
                        to=recipient.email,
                        html_body=render_transactional_email_html(
                            title=subject,
                            intro=(
                                f"Организатор запросил дополнительные файлы по заявке #{application_number}"
                                f"{f' ({competition_title})' if competition_title else ''}. "
                                f"Нужно прикрепить: {requested_types}."
                            ),
                            details_label="Комментарий организатора",
                            details=comment,
                            button_label="Загрузить файлы в ЛК",
                            button_url=detail_url,
                            status="warning",
                            status_label="Нужны файлы",
                        ),
                    )
                    notification_feed.publish(
                        recipient_id=recipient.id,
                        kind=NotificationKind.FILES_REQUESTED,
                        title=f"По заявке №{application_number} нужны файлы",
                        body=f"Что нужно прикрепить: {requested_types}. {comment}".strip(),
                        link=_cabinet_path(application_id),
                    )
                    messages = list(model.participant_messages or [])
                    messages.append(
                        {
                            "text": f"Email участнику: запрос недостающих файлов по заявке #{application_number} ({recipient.email})",
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
                application_id, receipt_refs, competition_id = _application_meta_for_submission(submission_id)
                if receipt_refs:
                    return Response({"detail": "Квитанция уже прикреплена, напоминание не требуется."}, status=400)
                recipient = UserModel.objects.filter(id=model.applicant_id, deleted_at__isnull=True).first()
                if recipient is None:
                    return Response({"detail": "Не найден получатель напоминания."}, status=400)
                competition_title = (
                    CompetitionModel.objects.filter(id=competition_id).values_list("title", flat=True).first() if competition_id else None
                )
                application_number = (application_id or submission_id)[:8].upper()
                subject = f"Напоминание об оплате заявки #{application_number}"
                body_text = (
                    f"Здравствуйте, {recipient.first_name}!\n\n"
                    f"Пожалуйста, прикрепите квитанцию об оплате по заявке #{application_number}"
                    f"{f' ({competition_title})' if competition_title else ''}.\n"
                    f"Откройте заявку: {_application_urls(application_id)[1]}\n"
                    "После прикрепления квитанции заявка будет готова к дальнейшей обработке.\n\n"
                    "С уважением,\nОргкомитет фестиваля"
                )
                _, detail_url = _application_urls(application_id)
                queue_review_email(
                    subject=subject,
                    body=body_text,
                    to=recipient.email,
                    html_body=render_transactional_email_html(
                        title=subject,
                        intro=(
                            f"Пожалуйста, прикрепите квитанцию об оплате по заявке #{application_number}"
                            f"{f' ({competition_title})' if competition_title else ''}."
                        ),
                        details_label="Что нужно сделать",
                        details="После прикрепления квитанции заявка будет готова к дальнейшей обработке.",
                        button_label="Открыть заявку в ЛК",
                        button_url=detail_url,
                        status="warning",
                        status_label="Ожидает квитанции",
                    ),
                )
                notification_feed.publish(
                    recipient_id=recipient.id,
                    kind=NotificationKind.PAYMENT_EXPECTED,
                    title=f"Напоминание об оплате заявки №{application_number}",
                    body="Прикрепите квитанцию об оплате, чтобы заявка пошла дальше.",
                    link=_cabinet_path(application_id),
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
                return Response({"detail": "Неизвестное действие."}, status=400)
        except ApplicationError as exc:
            return problems.application_problem(exc, instance=request.path, request=request)

        # Every branch above either returns or leaves a result, but nothing in the
        # structure enforces that — a new action that forgets to assign would have
        # raised AttributeError here and surfaced as a 500. An explicit guard turns
        # that into an honest conflict response.
        if result is None:
            return Response({"detail": "Действие не дало результата."}, status=409)

        body = {"id": result.submission.id, "status": result.submission.status, "capabilities": _capabilities(result.submission.status)}
        rid = problems.request_id(request)
        return Response({"data": body, "meta": {"requestId": rid}}, headers={"X-Request-ID": rid})


class OrganizerProcessingBulkView(_StaffView):
    def post(self, request: Request) -> Response:
        action = str(request.data.get("action") or "").strip()
        ids = request.data.get("ids") or []
        comment = str(request.data.get("comment", "")).strip()
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "Не выбрано ни одной заявки."}, status=400)
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


#: Characters a folder or file name may not carry into an archive.
_ARCHIVE_FORBIDDEN = str.maketrans(dict.fromkeys('/\\:*?"<>|', " "))


def _archive_safe(text: str) -> str:
    """``text`` as one path segment: no separators, no runs of spaces, never empty."""
    cleaned = " ".join(str(text).translate(_ARCHIVE_FORBIDDEN).split())
    return cleaned or "—"


def _application_folder(application: ApplicationModel) -> str:
    """The folder an order's paperwork goes in: who it is, then which order.

    The name alone is not enough — two Ивановых Анны are ordinary at a festival — so
    the order's short id follows it. Accounting reconciles against that id anyway.
    """
    refs = application.submission_refs or []
    lead = next((str(ref.get("participant_display_name") or "").strip() for ref in refs if ref.get("participant_display_name")), "")
    short = str(application.id).split("-")[0]
    return _archive_safe(f"{lead} — {short}" if lead else f"Заявка {short}")


class OrganizerProcessingDocumentsArchiveView(_StaffView):
    """``GET`` the orders' paperwork — receipts and benefit certificates — as one ZIP.

    Deliberately separate from the programme's backing tracks: this is the archive
    somebody reconciles payments and benefits from, and mixing the two would mean
    downloading gigabytes of audio to read four PDFs.

    Scoped with ``competitionId`` when given; without it, every order the organizer
    can see. One folder per order, so the receipts and the certificate justifying the
    amount sit together — the receipts first, because they are the documents the rest
    of the folder explains.

    An order settled by several transfers carries several receipts, and they are all
    included, numbered in upload order (``Квитанция 1``, ``Квитанция 2``, …) so the
    folder shows at a glance that the payment came in parts. A lone receipt keeps the
    plain name, because numbering one document reads as a missing second one.

    Orders with no receipt are named in the notes. That, and not the file count, is
    what somebody reconciling payments is looking for: an order carrying a benefit
    certificate but no proof of payment is precisely the case worth chasing, and
    counting documents would call it complete.
    """

    def get(self, request: Request) -> Any:
        competition_filter = (request.query_params.get("competitionId") or "").strip()
        # Scoped to the caller's own organization first, then narrowed by the
        # filter: an archive is a bulk download, and a bulk download is exactly
        # where a missing scope would hand over someone else's paperwork.
        visible = list(_visible_competitions(request).values_list("id", flat=True))
        applications = ApplicationModel.objects.filter(deleted_at__isnull=True, competition_id__in=visible)
        if competition_filter:
            applications = applications.filter(competition_id=competition_filter)
        applications = applications.order_by("created_at")

        members: list[ArchiveMember] = []
        without_receipt: list[str] = []
        for application in applications:
            folder = _application_folder(application)
            # ``file_reference``, not ``file``: an order's receipt and a submission's
            # attachment are stored under different keys, and only the attachment uses
            # the short one.
            receipts = _receipt_references(application.payment_receipts)
            for index, receipt in enumerate(receipts, start=1):
                caption = "Квитанция" if len(receipts) == 1 else f"Квитанция {index}"
                members.append(ArchiveMember(arcname=f"{folder}/{caption}{PurePosixPath(receipt).suffix.lower()}", reference=receipt))
            if not receipts:
                without_receipt.append(folder)
            submission_ids = [ref.get("submission_id") for ref in application.submission_refs or [] if ref.get("submission_id")]
            for row in SubmissionModel.objects.filter(id__in=submission_ids, deleted_at__isnull=True).values_list("attachments", flat=True):
                for entry in row or []:
                    if (entry or {}).get("type") != "BENEFIT":
                        continue
                    reference = str((entry or {}).get("file") or "").strip()
                    if not reference:
                        continue
                    caption = _archive_safe((entry or {}).get("caption") or "Документ о льготе")
                    members.append(ArchiveMember(arcname=f"{folder}/{caption}{PurePosixPath(reference).suffix.lower()}", reference=reference))

        notes = [f"Без квитанции: {folder}" for folder in without_receipt]
        return zip_response(members, filename="Документы заявок.zip", notes=notes)


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
                            " ".join(filter(None, [str(teacher.get("last_name") or ""), str(teacher.get("first_name") or "")])).strip(),
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
