"""``ApplicationMapper`` - the ACL between the ``Application`` (order) aggregate and its ORM row.

Serializes the order's cached submission references, service lines, consents, total
price and status history to JSON-safe primitives and rehydrates them back via
:meth:`Application.rehydrate`. Datetimes are ISO-8601 strings, money amounts decimal
strings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.applications.domain.entities import Application
from apps.applications.domain.value_objects import (
    ApplicationId,
    ApplicationStatus,
    ApplicationStatusChange,
    CompetitionId,
    Consent,
    Currency,
    EducationalOrganizationId,
    FileReference,
    Money,
    OrganizationName,
    PaymentReceipt,
    PriceSnapshot,
    ServiceId,
    ServiceLine,
    SubmissionId,
    SubmissionRef,
    SubmissionStatus,
    TotalPriceSnapshot,
    UserId,
)
from apps.applications.infrastructure.models import ApplicationModel

__all__ = ["ApplicationMapper"]


class ApplicationMapper:
    """Bidirectional, stateless translator between the ``Application`` aggregate and its row."""

    @staticmethod
    def to_domain(model: ApplicationModel) -> Application:
        """Reconstruct the ``Application`` aggregate from its row (no re-validation, no events)."""
        org_name = OrganizationName(model.organization_name) if model.organization_name is not None else None
        org_id = EducationalOrganizationId.from_uuid(model.educational_organization_id) if model.educational_organization_id is not None else None
        return Application.rehydrate(
            application_id=ApplicationId.from_uuid(model.id),
            competition_id=CompetitionId.from_uuid(model.competition_id),
            applicant_id=UserId.from_uuid(model.applicant_id),
            status=ApplicationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            educational_organization_id=org_id,
            organization_name=org_name,
            submission_refs=[ApplicationMapper._ref_from_json(row) for row in model.submission_refs],
            service_lines=[ApplicationMapper._service_from_json(row) for row in model.service_lines],
            consents=[ApplicationMapper._consent_from_json(row) for row in model.consents],
            total_price=ApplicationMapper._total_from_json(model.total_price),
            status_history=[ApplicationMapper._change_from_json(row) for row in model.status_history],
            payment_receipt=ApplicationMapper._receipt_from_json(model.payment_receipt),
            paid_at=model.paid_at,
            submitted_at=model.submitted_at,
            deleted_at=model.deleted_at,
            version=model.version,
        )

    @staticmethod
    def to_model(entity: Application) -> ApplicationModel:
        """Build a brand-new, **unsaved** ``ApplicationModel`` from an aggregate."""
        return ApplicationModel(**ApplicationMapper._to_columns(entity))

    @staticmethod
    def update_model(model: ApplicationModel, entity: Application) -> ApplicationModel:
        """Project ``entity`` onto an existing ``model`` in place, returning it."""
        for field, value in ApplicationMapper._to_columns(entity).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def _to_columns(entity: Application) -> dict[str, Any]:
        org = entity.organization_name
        return {
            "id": entity.id.value,
            "competition_id": entity.competition_id.value,
            "applicant_id": entity.applicant_id.value,
            "status": entity.status.value,
            "educational_organization_id": entity.educational_organization_id.value if entity.educational_organization_id is not None else None,
            "organization_name": org.value if org is not None else None,
            "submission_refs": [ApplicationMapper._ref_to_json(ref) for ref in entity.submission_refs],
            "service_lines": [ApplicationMapper._service_to_json(line) for line in entity.service_lines],
            "consents": [ApplicationMapper._consent_to_json(consent) for consent in entity.consents],
            "total_price": ApplicationMapper._total_to_json(entity.total_price),
            "status_history": [ApplicationMapper._change_to_json(change) for change in entity.status_history],
            "payment_receipt": ApplicationMapper._receipt_to_json(entity.payment_receipt),
            "paid_at": entity.paid_at,
            "submitted_at": entity.submitted_at,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "version": entity.version,
        }

    # ------------------------------------------------------------------
    # Submission references
    # ------------------------------------------------------------------

    @staticmethod
    def _ref_to_json(ref: SubmissionRef) -> dict[str, Any]:
        price = ref.price
        return {
            "submission_id": ref.submission_id.json(),
            "performance_title": ref.performance_title,
            "participant_display_name": ref.participant_display_name,
            "nomination": ref.nomination,
            "discipline": ref.discipline,
            "status": ref.status.value,
            "price": (
                {"amount": str(price.amount), "currency": price.currency.value, "calculated_at": price.calculated_at.isoformat()}
                if price is not None
                else None
            ),
        }

    @staticmethod
    def _ref_from_json(data: dict[str, Any]) -> SubmissionRef:
        price_data = data.get("price")
        price = (
            PriceSnapshot(
                price=Money.of(price_data["amount"], Currency(price_data["currency"])),
                calculated_at=datetime.fromisoformat(price_data["calculated_at"]),
            )
            if price_data is not None
            else None
        )
        return SubmissionRef(
            submission_id=SubmissionId.from_string(data["submission_id"]),
            performance_title=data["performance_title"],
            participant_display_name=data["participant_display_name"],
            nomination=data["nomination"],
            discipline=data["discipline"],
            status=SubmissionStatus(data["status"]),
            price=price,
        )

    # ------------------------------------------------------------------
    # Service lines / consents
    # ------------------------------------------------------------------

    @staticmethod
    def _service_to_json(line: ServiceLine) -> dict[str, Any]:
        return {
            "service_id": line.service_id.json(),
            "name": line.name,
            "unit_amount": str(line.unit_price.amount),
            "currency": line.unit_price.currency.value,
            "quantity": line.quantity,
        }

    @staticmethod
    def _service_from_json(data: dict[str, Any]) -> ServiceLine:
        return ServiceLine(
            service_id=ServiceId.from_string(data["service_id"]),
            name=data["name"],
            unit_price=Money.of(data["unit_amount"], Currency(data["currency"])),
            quantity=int(data["quantity"]),
        )

    @staticmethod
    def _consent_to_json(consent: Consent) -> dict[str, Any]:
        return {"code": consent.code, "version": consent.version, "accepted_at": consent.accepted_at.isoformat()}

    @staticmethod
    def _consent_from_json(data: dict[str, Any]) -> Consent:
        return Consent(code=data["code"], version=data["version"], accepted_at=datetime.fromisoformat(data["accepted_at"]))

    # ------------------------------------------------------------------
    # Total price / status history
    # ------------------------------------------------------------------

    @staticmethod
    def _total_to_json(total: TotalPriceSnapshot | None) -> dict[str, Any] | None:
        if total is None:
            return None
        return {
            "total": str(total.total.amount),
            "submissions_total": str(total.submissions_total.amount),
            "services_total": str(total.services_total.amount),
            "currency": total.total.currency.value,
            "calculated_at": total.calculated_at.isoformat(),
        }

    @staticmethod
    def _total_from_json(data: dict[str, Any] | None) -> TotalPriceSnapshot | None:
        if data is None:
            return None
        currency = Currency(data["currency"])
        return TotalPriceSnapshot(
            total=Money.of(data["total"], currency),
            submissions_total=Money.of(data["submissions_total"], currency),
            services_total=Money.of(data["services_total"], currency),
            calculated_at=datetime.fromisoformat(data["calculated_at"]),
        )

    @staticmethod
    def _change_to_json(change: ApplicationStatusChange) -> dict[str, Any]:
        return {
            "from_status": change.from_status.value if change.from_status is not None else None,
            "to_status": change.to_status.value,
            "occurred_at": change.occurred_at.isoformat(),
        }

    @staticmethod
    def _change_from_json(data: dict[str, Any]) -> ApplicationStatusChange:
        return ApplicationStatusChange(
            from_status=ApplicationStatus(data["from_status"]) if data["from_status"] is not None else None,
            to_status=ApplicationStatus(data["to_status"]),
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
        )

    @staticmethod
    def _receipt_to_json(receipt: PaymentReceipt | None) -> dict[str, Any] | None:
        if receipt is None:
            return None
        return {"file_reference": receipt.file.value, "uploaded_at": receipt.uploaded_at.isoformat()}

    @staticmethod
    def _receipt_from_json(data: dict[str, Any] | None) -> PaymentReceipt | None:
        if not data:
            return None
        return PaymentReceipt(file=FileReference(data["file_reference"]), uploaded_at=datetime.fromisoformat(data["uploaded_at"]))
