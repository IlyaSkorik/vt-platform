"""The settings JSON ACL: what a stored blob means when it does not say.

The competitions ``settings`` column is deliberately schema-less and append-only, so
every flag is read through a default and a row written under an older shape has to
keep loading. The interesting cases are therefore not the round trip — that is one
dict — but the *absences*: a blob that predates a flag, and a blob from before the
settings module existed at all.
"""

from __future__ import annotations

from apps.competitions.domain.value_objects import CompetitionSettings, JudgingMode
from apps.competitions.infrastructure.mappers.settings_json import settings_from_json, settings_to_json


def test_the_flag_survives_a_round_trip() -> None:
    stored = settings_to_json(CompetitionSettings.default().with_changes(allow_multiple_performances=False))

    assert stored["schema_version"] == 7
    assert settings_from_json(stored).allow_multiple_performances is False


def test_a_blob_written_before_the_flag_existed_keeps_allowing_several() -> None:
    """Schema 3 has no opinion here, and narrowing a festival nobody reconfigured
    would silently break orders already being filled in."""
    stored = settings_to_json(CompetitionSettings.default())
    del stored["allow_multiple_performances"]
    stored["schema_version"] = 3

    assert settings_from_json(stored).allow_multiple_performances is True


def test_a_pre_settings_module_bag_keeps_allowing_several() -> None:
    legacy = {"allow_multiple_applications": True, "require_teacher": False}

    assert settings_from_json(legacy).allow_multiple_performances is True


def test_a_blob_written_before_the_payer_flag_existed_collects_no_payer() -> None:
    """Schema 4 has no opinion here, and switching the block on for a festival nobody
    reconfigured would block orders already being filled in."""
    stored = settings_to_json(CompetitionSettings.default())
    del stored["collect_payer_details"]
    stored["schema_version"] = 4

    assert settings_from_json(stored).collect_payer_details is False


def test_a_pre_settings_module_bag_collects_no_payer() -> None:
    legacy = {"allow_multiple_applications": True, "require_teacher": False}

    assert settings_from_json(legacy).collect_payer_details is False


def test_the_payer_flag_survives_a_round_trip() -> None:
    stored = settings_to_json(CompetitionSettings.default().with_changes(collect_payer_details=True))

    assert settings_from_json(stored).collect_payer_details is True


def test_a_schema_5_blob_is_not_mistaken_for_a_legacy_bag() -> None:
    """The reader gates on the version, so a new number must be on the modern path —
    otherwise every flag would silently fall back to the legacy mapping."""
    stored = settings_to_json(CompetitionSettings.default().with_changes(require_teacher=False, allow_replacing_documents=False))

    loaded = settings_from_json(stored)

    assert loaded.require_teacher is False
    assert loaded.allow_replacing_documents is False


def test_a_blob_written_before_online_judging_existed_runs_on_protocols() -> None:
    """Schema 5 has no opinion here, and every festival configured before online
    judging existed was running its jury off paper and a protocol."""
    stored = settings_to_json(CompetitionSettings.default())
    del stored["judging_mode"]
    stored["schema_version"] = 5

    assert settings_from_json(stored).judging_mode is JudgingMode.PROTOCOLS


def test_the_judging_mode_survives_a_round_trip() -> None:
    stored = settings_to_json(CompetitionSettings.default().with_changes(judging_mode=JudgingMode.ONLINE))

    assert stored["judging_mode"] == "ONLINE"
    assert settings_from_json(stored).judging_mode is JudgingMode.ONLINE


def test_an_unreadable_judging_mode_falls_back_to_protocols() -> None:
    """A hand-edited column must not leave a festival in a mode that does not exist."""
    stored = settings_to_json(CompetitionSettings.default())
    stored["judging_mode"] = "SOMETHING_ELSE"

    assert settings_from_json(stored).judging_mode is JudgingMode.PROTOCOLS


def test_a_blob_written_before_the_sweep_switch_existed_keeps_auto_cancelling() -> None:
    """Schema 6 has no opinion here, and every festival configured before the switch
    existed was having its unpaid orders swept all the same."""
    stored = settings_to_json(CompetitionSettings.default())
    del stored["auto_cancel_unpaid_applications"]
    stored["schema_version"] = 6

    assert settings_from_json(stored).auto_cancel_unpaid_applications is True


def test_a_pre_settings_module_bag_keeps_auto_cancelling() -> None:
    legacy = {"allow_multiple_applications": True, "require_teacher": False}

    assert settings_from_json(legacy).auto_cancel_unpaid_applications is True


def test_turning_the_sweep_off_survives_a_round_trip() -> None:
    stored = settings_to_json(CompetitionSettings.default().with_changes(auto_cancel_unpaid_applications=False))

    assert stored["auto_cancel_unpaid_applications"] is False
    assert settings_from_json(stored).auto_cancel_unpaid_applications is False
