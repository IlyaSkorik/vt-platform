"""Settings JSON ACL helpers for the Competition aggregate.

Separated so the mapper can translate the nested
:class:`~apps.competitions.domain.value_objects.CompetitionSettings` graph to/from
the root row's JSON column without treating every field as a boolean.
"""

from __future__ import annotations

from apps.competitions.domain.value_objects import (
    CompetitionSettings,
    MusicRequirements,
    ParticipationFormatId,
    ParticipationFormatRequirements,
    PaymentMethod,
    PaymentReceiptRequirements,
    PaymentTiming,
    VideoProvider,
    VideoRequirements,
    VideoSubmissionMode,
)

__all__ = ["settings_from_json", "settings_to_json"]


def settings_to_json(settings: CompetitionSettings) -> dict[str, object]:
    """Serialize settings for the competitions.settings JSON column."""
    return {
        "schema_version": 2,
        "allow_multiple_applications": settings.allow_multiple_applications,
        "allow_application_editing": settings.allow_application_editing,
        "allow_withdrawing_applications": settings.allow_withdrawing_applications,
        "allow_copying_previous_applications": settings.allow_copying_previous_applications,
        "require_teacher": settings.require_teacher,
        "require_parent_guardian": settings.require_parent_guardian,
        "participant_comment_enabled": settings.participant_comment_enabled,
        "require_document_upload": settings.require_document_upload,
        "allow_additional_documents_later": settings.allow_additional_documents_later,
        "allow_replacing_documents": settings.allow_replacing_documents,
        "payment_required": settings.payment_required,
        "payment_timing": settings.payment_timing.value,
        "payment_methods": [method.value for method in settings.payment_methods],
        "require_personal_data_consent": settings.require_personal_data_consent,
        "require_media_consent": settings.require_media_consent,
        "require_regulations_acceptance": settings.require_regulations_acceptance,
        "email_notifications": settings.email_notifications,
        "cabinet_notifications": settings.cabinet_notifications,
        "sms_notifications": settings.sms_notifications,
        "push_notifications": settings.push_notifications,
        "manual_application_approval": settings.manual_application_approval,
        "automatic_approval_after_payment": settings.automatic_approval_after_payment,
        "allow_returning_for_correction": settings.allow_returning_for_correction,
        "format_requirements": [_format_requirements_to_json(item) for item in settings.format_requirements],
    }


def settings_from_json(data: object) -> CompetitionSettings:
    """Rebuild settings from JSON, migrating legacy flat boolean bags."""
    default = CompetitionSettings.default()
    if not isinstance(data, dict):
        return default
    if data.get("schema_version") == 2 or "payment_timing" in data or "format_requirements" in data:
        return _from_v2(data, default)
    return _from_legacy(data, default)


def _from_legacy(data: dict[str, object], default: CompetitionSettings) -> CompetitionSettings:
    """Map the pre-settings-module flat boolean bag onto the new shape."""
    return CompetitionSettings(
        allow_multiple_applications=bool(data.get("allow_multiple_applications", default.allow_multiple_applications)),
        allow_application_editing=bool(data.get("allow_application_editing", default.allow_application_editing)),
        allow_withdrawing_applications=bool(
            data.get("allow_participant_changes", default.allow_withdrawing_applications)
        ),
        allow_copying_previous_applications=False,
        require_teacher=bool(data.get("require_teacher", default.require_teacher)),
        require_parent_guardian=bool(data.get("require_parent_consent", default.require_parent_guardian)),
        participant_comment_enabled=bool(
            data.get("require_comment_for_application", default.participant_comment_enabled)
        ),
        require_document_upload=bool(data.get("require_identity_document", default.require_document_upload)),
        allow_additional_documents_later=True,
        allow_replacing_documents=True,
        payment_required=False,
        payment_timing=PaymentTiming.BEFORE_APPROVAL,
        payment_methods=(),
        require_personal_data_consent=bool(data.get("require_parent_consent", default.require_personal_data_consent)),
        require_media_consent=False,
        require_regulations_acceptance=True,
        email_notifications=True,
        cabinet_notifications=True,
        sms_notifications=False,
        push_notifications=False,
        manual_application_approval=True,
        automatic_approval_after_payment=False,
        allow_returning_for_correction=True,
        format_requirements=(),
    )


def _from_v2(data: dict[str, object], default: CompetitionSettings) -> CompetitionSettings:
    timing_raw = data.get("payment_timing", default.payment_timing.value)
    try:
        timing = PaymentTiming(str(timing_raw))
    except ValueError:
        timing = default.payment_timing

    methods_raw = data.get("payment_methods", [])
    methods: list[PaymentMethod] = []
    if isinstance(methods_raw, list):
        for item in methods_raw:
            try:
                methods.append(PaymentMethod(str(item)))
            except ValueError:
                continue

    format_raw = data.get("format_requirements", [])
    format_requirements: list[ParticipationFormatRequirements] = []
    if isinstance(format_raw, list):
        for item in format_raw:
            if isinstance(item, dict):
                parsed = _format_requirements_from_json(item)
                if parsed is not None:
                    format_requirements.append(parsed)

    return CompetitionSettings(
        allow_multiple_applications=bool(data.get("allow_multiple_applications", default.allow_multiple_applications)),
        allow_application_editing=bool(data.get("allow_application_editing", default.allow_application_editing)),
        allow_withdrawing_applications=bool(
            data.get("allow_withdrawing_applications", default.allow_withdrawing_applications)
        ),
        allow_copying_previous_applications=bool(
            data.get("allow_copying_previous_applications", default.allow_copying_previous_applications)
        ),
        require_teacher=bool(data.get("require_teacher", default.require_teacher)),
        require_parent_guardian=bool(data.get("require_parent_guardian", default.require_parent_guardian)),
        participant_comment_enabled=bool(
            data.get("participant_comment_enabled", default.participant_comment_enabled)
        ),
        require_document_upload=bool(data.get("require_document_upload", default.require_document_upload)),
        allow_additional_documents_later=bool(
            data.get("allow_additional_documents_later", default.allow_additional_documents_later)
        ),
        allow_replacing_documents=bool(data.get("allow_replacing_documents", default.allow_replacing_documents)),
        payment_required=bool(data.get("payment_required", default.payment_required)),
        payment_timing=timing,
        payment_methods=tuple(methods),
        require_personal_data_consent=bool(
            data.get("require_personal_data_consent", default.require_personal_data_consent)
        ),
        require_media_consent=bool(data.get("require_media_consent", default.require_media_consent)),
        require_regulations_acceptance=bool(
            data.get("require_regulations_acceptance", default.require_regulations_acceptance)
        ),
        email_notifications=bool(data.get("email_notifications", default.email_notifications)),
        cabinet_notifications=bool(data.get("cabinet_notifications", default.cabinet_notifications)),
        sms_notifications=bool(data.get("sms_notifications", default.sms_notifications)),
        push_notifications=bool(data.get("push_notifications", default.push_notifications)),
        manual_application_approval=bool(
            data.get("manual_application_approval", default.manual_application_approval)
        ),
        automatic_approval_after_payment=bool(
            data.get("automatic_approval_after_payment", default.automatic_approval_after_payment)
        ),
        allow_returning_for_correction=bool(
            data.get("allow_returning_for_correction", default.allow_returning_for_correction)
        ),
        format_requirements=tuple(format_requirements),
    )


def _format_requirements_to_json(item: ParticipationFormatRequirements) -> dict[str, object]:
    return {
        "participation_format_id": item.participation_format_id.json(),
        "music": {
            "require_upload": item.music.require_upload,
            "allow_replacement": item.music.allow_replacement,
            "allowed_formats": list(item.music.allowed_formats),
            "max_upload_size_mb": item.music.max_upload_size_mb,
        },
        "video": {
            "mode": item.video.mode.value,
            "allowed_providers": [provider.value for provider in item.video.allowed_providers],
            "allow_replacement": item.video.allow_replacement,
        },
        "payment_receipt": {
            "require_receipt": item.payment_receipt.require_receipt,
            "allow_upload_later": item.payment_receipt.allow_upload_later,
            "allow_replacement": item.payment_receipt.allow_replacement,
        },
    }


def _format_requirements_from_json(data: dict[str, object]) -> ParticipationFormatRequirements | None:
    raw_id = data.get("participation_format_id")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    try:
        format_id = ParticipationFormatId.from_string(raw_id)
    except Exception:
        return None

    music_data = data.get("music") if isinstance(data.get("music"), dict) else {}
    video_data = data.get("video") if isinstance(data.get("video"), dict) else {}
    receipt_data = data.get("payment_receipt") if isinstance(data.get("payment_receipt"), dict) else {}
    assert isinstance(music_data, dict)
    assert isinstance(video_data, dict)
    assert isinstance(receipt_data, dict)

    formats_raw = music_data.get("allowed_formats", [])
    formats = tuple(str(item) for item in formats_raw) if isinstance(formats_raw, list) else ()

    try:
        mode = VideoSubmissionMode(str(video_data.get("mode", VideoSubmissionMode.NOT_REQUIRED.value)))
    except ValueError:
        mode = VideoSubmissionMode.NOT_REQUIRED

    providers_raw = video_data.get("allowed_providers", [])
    providers: list[VideoProvider] = []
    if isinstance(providers_raw, list):
        for item in providers_raw:
            try:
                providers.append(VideoProvider(str(item)))
            except ValueError:
                continue

    max_size = music_data.get("max_upload_size_mb", 25)
    try:
        max_upload_size_mb = int(max_size)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        max_upload_size_mb = 25

    return ParticipationFormatRequirements(
        participation_format_id=format_id,
        music=MusicRequirements(
            require_upload=bool(music_data.get("require_upload", False)),
            allow_replacement=bool(music_data.get("allow_replacement", True)),
            allowed_formats=formats,
            max_upload_size_mb=max_upload_size_mb,
        ),
        video=VideoRequirements(
            mode=mode,
            allowed_providers=tuple(providers),
            allow_replacement=bool(video_data.get("allow_replacement", True)),
        ),
        payment_receipt=PaymentReceiptRequirements(
            require_receipt=bool(receipt_data.get("require_receipt", False)),
            allow_upload_later=bool(receipt_data.get("allow_upload_later", True)),
            allow_replacement=bool(receipt_data.get("allow_replacement", True)),
        ),
    )
