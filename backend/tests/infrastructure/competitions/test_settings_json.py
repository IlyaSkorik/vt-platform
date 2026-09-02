"""The settings JSON ACL: what a stored blob means when it does not say.

The competitions ``settings`` column is deliberately schema-less and append-only, so
every flag is read through a default and a row written under an older shape has to
keep loading. The interesting cases are therefore not the round trip — that is one
dict — but the *absences*: a blob that predates a flag, and a blob from before the
settings module existed at all.
"""

from __future__ import annotations

from apps.competitions.domain.value_objects import CompetitionSettings
from apps.competitions.infrastructure.mappers.settings_json import settings_from_json, settings_to_json


def test_the_flag_survives_a_round_trip() -> None:
    stored = settings_to_json(CompetitionSettings.default().with_changes(allow_multiple_performances=False))

    assert stored["schema_version"] == 4
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


def test_a_schema_4_blob_is_not_mistaken_for_a_legacy_bag() -> None:
    """The reader gates on the version, so a new number must be on the modern path —
    otherwise every flag would silently fall back to the legacy mapping."""
    stored = settings_to_json(CompetitionSettings.default().with_changes(require_teacher=False, allow_replacing_documents=False))

    loaded = settings_from_json(stored)

    assert loaded.require_teacher is False
    assert loaded.allow_replacing_documents is False
