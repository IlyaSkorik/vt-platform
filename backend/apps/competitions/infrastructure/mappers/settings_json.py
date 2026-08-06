"""Settings JSON ACL helpers for the Competition aggregate.

Separated so the mapper can translate the nested
:class:`~apps.competitions.domain.value_objects.CompetitionSettings` graph to/from
the root row's JSON column without treating every field as a boolean.
"""

from __future__ import annotations

from apps.competitions.domain.value_objects import (
    _DEFAULT_AUDIO_FORMATS,
    _DEFAULT_VIDEO_FORMATS,
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
from shared.utils.json_values import as_int

__all__ = ["settings_from_json", "settings_to_json"]


def settings_to_json(settings: CompetitionSettings) -> dict[str, object]:
    """Serialize settings for the competitions.settings JSON column."""
    return {
        "schema_version": 3,
        "allow_multiple_applications": settings.allow_multiple_applications,
        "allow_application_editing": settings.allow_application_editing,
        "allow_withdrawing_applications": settings.allow_withdrawing_applications,
        "require_teacher": settings.require_teacher,
        "require_parent_guardian": settings.require_parent_guardian,
        "participant_comment_enabled": settings.participant_comment_enabled,
        "require_document_upload": settings.require_document_upload,
        "allow_additional_documents_later": settings.allow_additional_documents_later,
        "allow_replacing_documents": settings.allow_replacing_documents,
        "payment_required": settings.payment_required,
        "payment_timing": settings.payment_timing.value,
        "payment_methods": [method.value for method in settings.payment_methods],
        "additional_performance_discount_percent": settings.additional_performance_discount_percent,
        "require_personal_data_consent": settings.require_personal_data_consent,
        "require_media_consent": settings.require_media_consent,
        "require_regulations_acceptance": settings.require_regulations_acceptance,
        "manual_application_approval": settings.manual_application_approval,
        "automatic_approval_after_payment": settings.automatic_approval_after_payment,
        "allow_returning_for_correction": settings.allow_returning_for_correction,
        "format_requirements": [_format_requirements_to_json(item) for item in settings.format_requirements],
    }


def settings_from_json(data: object) -> CompetitionSettings:
    """Rebuild settings from JSON, migrating legacy flat boolean bags.

    Schemas 2 and 3 share a shape — 3 only *drops* keys (notification channels and
    previous-application copying), and unknown keys are ignored — so one reader
    serves both. Rows still holding schema-2 keys are read fine and rewritten as 3
    on the next save.
    """
    default = CompetitionSettings.default()
    if not isinstance(data, dict):
        return default
    if data.get("schema_version") in {2, 3} or "payment_timing" in data or "format_requirements" in data:
        return _from_modern(data, default)
    return _from_legacy(data, default)


def _from_legacy(data: dict[str, object], default: CompetitionSettings) -> CompetitionSettings:
    """Map the pre-settings-module flat boolean bag onto the new shape."""
    return CompetitionSettings(
        allow_multiple_applications=bool(data.get("allow_multiple_applications", default.allow_multiple_applications)),
        allow_application_editing=bool(data.get("allow_application_editing", default.allow_application_editing)),
        allow_withdrawing_applications=bool(data.get("allow_participant_changes", default.allow_withdrawing_applications)),
        require_teacher=bool(data.get("require_teacher", default.require_teacher)),
        require_parent_guardian=bool(data.get("require_parent_consent", default.require_parent_guardian)),
        participant_comment_enabled=bool(data.get("require_comment_for_application", default.participant_comment_enabled)),
        require_document_upload=bool(data.get("require_identity_document", default.require_document_upload)),
        allow_additional_documents_later=True,
        allow_replacing_documents=True,
        payment_required=False,
        payment_timing=PaymentTiming.BEFORE_APPROVAL,
        payment_methods=(),
        require_personal_data_consent=bool(data.get("require_parent_consent", default.require_personal_data_consent)),
        require_media_consent=False,
        require_regulations_acceptance=True,
        manual_application_approval=True,
        automatic_approval_after_payment=False,
        allow_returning_for_correction=True,
        format_requirements=(),
    )


def _from_modern(data: dict[str, object], default: CompetitionSettings) -> CompetitionSettings:
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

    discount_percent = as_int(
        data.get("additional_performance_discount_percent"),
        default=default.additional_performance_discount_percent,
    )

    return CompetitionSettings(
        allow_multiple_applications=bool(data.get("allow_multiple_applications", default.allow_multiple_applications)),
        allow_application_editing=bool(data.get("allow_application_editing", default.allow_application_editing)),
        allow_withdrawing_applications=bool(data.get("allow_withdrawing_applications", default.allow_withdrawing_applications)),
        require_teacher=bool(data.get("require_teacher", default.require_teacher)),
        require_parent_guardian=bool(data.get("require_parent_guardian", default.require_parent_guardian)),
        participant_comment_enabled=bool(data.get("participant_comment_enabled", default.participant_comment_enabled)),
        require_document_upload=bool(data.get("require_document_upload", default.require_document_upload)),
        allow_additional_documents_later=bool(data.get("allow_additional_documents_later", default.allow_additional_documents_later)),
        allow_replacing_documents=bool(data.get("allow_replacing_documents", default.allow_replacing_documents)),
        payment_required=bool(data.get("payment_required", default.payment_required)),
        payment_timing=timing,
        payment_methods=tuple(methods),
        additional_performance_discount_percent=discount_percent,
        require_personal_data_consent=bool(data.get("require_personal_data_consent", default.require_personal_data_consent)),
        require_media_consent=bool(data.get("require_media_consent", default.require_media_consent)),
        require_regulations_acceptance=bool(data.get("require_regulations_acceptance", default.require_regulations_acceptance)),
        manual_application_approval=bool(data.get("manual_application_approval", default.manual_application_approval)),
        automatic_approval_after_payment=bool(data.get("automatic_approval_after_payment", default.automatic_approval_after_payment)),
        allow_returning_for_correction=bool(data.get("allow_returning_for_correction", default.allow_returning_for_correction)),
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
            "allowed_formats": list(item.video.allowed_formats),
            "max_upload_size_mb": item.video.max_upload_size_mb,
        },
        "payment_receipt": {
            "require_receipt": item.payment_receipt.require_receipt,
            "allow_upload_later": item.payment_receipt.allow_upload_later,
            "allow_replacement": item.payment_receipt.allow_replacement,
        },
    }


def _formats(raw: object, *, default: tuple[str, ...]) -> tuple[str, ...]:
    """Extension list off a stored blob, falling back to the kind's default.

    An empty or malformed list reads as "not configured": the value object refuses to
    accept a format-less requirement that allows uploads, so handing it the default is
    the only reading that both loads and stays valid.
    """
    if not isinstance(raw, list):
        return default
    parsed = tuple(str(item) for item in raw if str(item).strip())
    return parsed or default


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

    max_upload_size_mb = as_int(music_data.get("max_upload_size_mb"), default=25)

    return ParticipationFormatRequirements(
        participation_format_id=format_id,
        music=MusicRequirements(
            require_upload=bool(music_data.get("require_upload", False)),
            allow_replacement=bool(music_data.get("allow_replacement", True)),
            allowed_formats=_formats(music_data.get("allowed_formats"), default=_DEFAULT_AUDIO_FORMATS),
            max_upload_size_mb=max_upload_size_mb,
        ),
        video=VideoRequirements(
            mode=mode,
            allowed_providers=tuple(providers),
            allow_replacement=bool(video_data.get("allow_replacement", True)),
            allowed_formats=_formats(video_data.get("allowed_formats"), default=_DEFAULT_VIDEO_FORMATS),
            max_upload_size_mb=as_int(video_data.get("max_upload_size_mb"), default=200),
        ),
        payment_receipt=PaymentReceiptRequirements(
            require_receipt=bool(receipt_data.get("require_receipt", False)),
            allow_upload_later=bool(receipt_data.get("allow_upload_later", True)),
            allow_replacement=bool(receipt_data.get("allow_replacement", True)),
        ),
    )
