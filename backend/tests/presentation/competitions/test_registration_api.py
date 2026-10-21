"""Integration tests for the public Registration read projection.

``GET /api/v1/public/competitions/{id}/registration`` — the single, unauthenticated
projection the Registration Wizard consumes. Exercised end to end against real
PostgreSQL: a seeded competition is projected through the Competition aggregate.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.competitions.infrastructure.models.base import uuid7

pytestmark = pytest.mark.django_db


def _seed_competition(*, status: str = "PUBLISHED", open_nomination: bool = True, waitlisted_nomination: bool = False) -> str:
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status=status, title="Spring Festival", season="2025/2026")
    if open_nomination:
        # Registration is scheduled per nomination; an open window makes the competition
        # accept applications (its top-level registrationOpen becomes true).
        CategoryModel.objects.create(
            competition=competition,
            name="Vocal",
            registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
            registration_closes_at=datetime(2100, 1, 1, tzinfo=UTC),
        )
    if waitlisted_nomination:
        # A genre whose window has already passed but which keeps a queue behind it.
        CategoryModel.objects.create(
            competition=competition,
            name="Choreography",
            registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
            registration_closes_at=datetime(2001, 1, 1, tzinfo=UTC),
            waitlist_enabled=True,
        )
    return str(competition.id)


def _url(competition_id: str) -> str:
    return f"/api/v1/public/competitions/{competition_id}/registration"


def test_returns_single_projection_for_open_competition() -> None:
    competition_id = _seed_competition()
    response = APIClient().get(_url(competition_id))
    assert response.status_code == 200, response.data
    data = response.data["data"]
    assert data["competition"]["id"] == competition_id
    assert data["competition"]["title"] == "Spring Festival"
    assert data["registrationOpen"] is True
    # The open nomination is projected with its per-nomination registration state.
    assert len(data["nominations"]) == 1
    nomination = data["nominations"][0]
    assert nomination["registrationOpen"] is True
    assert nomination["registrationStopped"] is False
    assert nomination["registrationOpensAt"] is not None
    assert nomination["registrationClosesAt"] is not None
    # Every config axis the wizard needs is present as a (possibly empty) list.
    for key in (
        "nominations",
        "disciplines",
        "ageCategories",
        "participantGroups",
        "participationFormats",
        "admissionRules",
        "additionalServices",
        "requiredConsents",
        "uploadRequirements",
    ):
        assert key in data
        assert isinstance(data[key], list)
    # Two consents are the platform's, not the organizer's: a child's data is held on
    # the representative's consent and results are published on consent to
    # distribution, so neither is a setting a festival can switch off
    # (LEGAL-001 §4.1, §8.3).
    codes = {consent["code"]: consent["required"] for consent in data["requiredConsents"]}
    assert codes["personal_data"] is True
    assert codes["distribution"] is True
    # The festival decides on these.
    assert "media" in codes
    assert "regulations" in codes
    # Offered always, required never: withholding it only means the work is not
    # published in the open sections (LEGAL-001 §8.5).
    assert codes["work_publication"] is False


def test_the_projection_carries_the_multiple_performance_rule() -> None:
    """The wizard hides «Добавить выступление» off this flag, so it has to be here.

    Default on, because a festival narrows the rule rather than having to widen it —
    and because the projection is the only place the participant's side can read it.
    """
    competition_id = _seed_competition()

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["allowMultiplePerformances"] is True


def test_turning_the_rule_off_shows_up_in_the_projection() -> None:
    from apps.competitions.infrastructure.models import CompetitionModel

    competition_id = _seed_competition()
    competition = CompetitionModel.objects.get(id=competition_id)
    competition.settings = {**competition.settings, "schema_version": 5, "allow_multiple_performances": False}
    competition.save(update_fields=["settings"])

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["allowMultiplePerformances"] is False


def test_the_payer_block_is_off_unless_the_festival_asks_for_it() -> None:
    """The wizard renders the block off this flag, so a festival nobody configured must
    not start demanding a name it will never use."""
    competition_id = _seed_competition()

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["collectPayerDetails"] is False


def test_turning_the_payer_block_on_shows_up_in_the_projection() -> None:
    from apps.competitions.infrastructure.models import CompetitionModel

    competition_id = _seed_competition()
    competition = CompetitionModel.objects.get(id=competition_id)
    competition.settings = {**competition.settings, "schema_version": 5, "collect_payer_details": True}
    competition.save(update_fields=["settings"])

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["collectPayerDetails"] is True


def test_the_participant_note_is_offered_by_default() -> None:
    """The wizard renders the free-form note off this flag.

    Default on: a festival that never configured anything still lets an applicant say
    the number needs a microphone, and saying nothing stays the norm either way.
    """
    competition_id = _seed_competition()

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["participantCommentEnabled"] is True


def test_switching_the_participant_note_off_shows_up_in_the_projection() -> None:
    """Off means the field is not rendered at all — the Applications context refuses a
    submission that carries a note, so the wizard must know not to offer one."""
    from apps.competitions.infrastructure.models import CompetitionModel

    competition_id = _seed_competition()
    competition = CompetitionModel.objects.get(id=competition_id)
    competition.settings = {**competition.settings, "schema_version": 5, "participant_comment_enabled": False}
    competition.save(update_fields=["settings"])

    response = APIClient().get(_url(competition_id))

    assert response.data["data"]["participantCommentEnabled"] is False


def test_mixed_age_category_is_projected_with_its_calculation_method() -> None:
    # The wizard asks the applicant what ages a mixed group is, so it has to be able to
    # tell a mixed band from a standard one — and to say how the organizer will read
    # the answer back to a single age.
    from apps.competitions.infrastructure.models import AgeCategoryModel, CompetitionModel

    competition_id = _seed_competition()
    competition = CompetitionModel.objects.get(id=competition_id)
    group_id = uuid7()
    AgeCategoryModel.objects.create(competition=competition, participant_group_id=group_id, name="7–10 лет", min_age=7, max_age=10)
    AgeCategoryModel.objects.create(
        competition=competition,
        participant_group_id=group_id,
        name="Смешанная",
        min_age=5,
        max_age=60,
        type="MIXED",
        mixed_calculation_method="AVERAGE",
        sort_order=1,
    )

    response = APIClient().get(_url(competition_id))

    assert response.status_code == 200, response.data
    by_name = {band["name"]: band for band in response.data["data"]["ageCategories"]}
    assert by_name["7–10 лет"]["type"] == "STANDARD"
    assert by_name["7–10 лет"]["mixedCalculationMethod"] is None
    assert by_name["Смешанная"]["type"] == "MIXED"
    assert by_name["Смешанная"]["mixedCalculationMethod"] == "AVERAGE"


def test_a_closed_genre_with_a_queue_is_projected_as_such() -> None:
    competition_id = _seed_competition(open_nomination=False, waitlisted_nomination=True)
    response = APIClient().get(_url(competition_id))
    assert response.status_code == 200, response.data
    data = response.data["data"]
    # Registration really is over — the wizard says so — but the door is not bolted.
    assert data["registrationOpen"] is False
    assert data["waitlistOpen"] is True
    nomination = data["nominations"][0]
    assert nomination["registrationOpen"] is False
    assert nomination["waitlistEnabled"] is True
    assert nomination["waitlistOpen"] is True


def test_an_open_genre_offers_no_queue_even_with_the_setting_on() -> None:
    # Both doors open at once would let an applicant pick the unpaid one.
    competition_id = _seed_competition(open_nomination=True, waitlisted_nomination=False)
    from apps.competitions.infrastructure.models import CategoryModel

    CategoryModel.objects.filter(competition_id=uuid.UUID(competition_id)).update(waitlist_enabled=True)
    response = APIClient().get(_url(competition_id))
    data = response.data["data"]
    assert data["waitlistOpen"] is False
    nomination = data["nominations"][0]
    assert nomination["registrationOpen"] is True
    assert nomination["waitlistEnabled"] is True
    assert nomination["waitlistOpen"] is False


def test_a_closed_genre_without_a_queue_stays_shut() -> None:
    competition_id = _seed_competition(open_nomination=False, waitlisted_nomination=False)
    response = APIClient().get(_url(competition_id))
    data = response.data["data"]
    assert data["registrationOpen"] is False
    assert data["waitlistOpen"] is False


def test_unauthenticated_access_is_allowed() -> None:
    competition_id = _seed_competition()
    # No Authorization header at all.
    assert APIClient().get(_url(competition_id)).status_code == 200


def test_unknown_competition_is_404_problem() -> None:
    response = APIClient().get(_url(str(uuid7())))
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"


def test_malformed_id_is_404_not_500() -> None:
    assert APIClient().get(_url("not-a-uuid")).status_code == 404


def test_draft_competition_is_hidden() -> None:
    competition_id = _seed_competition(status="DRAFT")
    assert APIClient().get(_url(competition_id)).status_code == 404


def test_v4_uuid_is_hidden() -> None:
    # A well-formed but non-v7 id never matches a real competition id.
    assert APIClient().get(_url(str(uuid.uuid4()))).status_code == 404


def test_upload_requirements_carry_the_media_limits() -> None:
    # An in-person festival collects the file for the hall's screen, so the wizard needs
    # the same two facts for video it already has for music: which extensions and how
    # large. Sent whatever the mode is, so the client never invents a limit of its own
    # that the server would then enforce differently.
    competition_id = _seed_competition()
    data = APIClient().get(_url(competition_id)).data["data"]

    for requirement in data["uploadRequirements"]:
        assert isinstance(requirement["mediaAllowedFormats"], list)
        assert requirement["mediaAllowedFormats"]
        assert requirement["mediaMaxTotalSizeMb"] >= 1
        # Whether the video is a condition of entry travels too: the wizard labels the
        # control and blocks submission on it, and it must not guess.
        assert isinstance(requirement["mediaRequired"], bool)


def test_the_file_windows_are_open_while_the_festival_is() -> None:
    # Unset upload deadlines mean no cut-off, and the projection says so plainly —
    # the cabinet renders its upload cards off these three and nothing else.
    competition_id = _seed_competition()

    data = APIClient().get(_url(competition_id)).data["data"]

    assert data["musicUploadOpen"] is True
    assert data["mediaUploadOpen"] is True
    assert data["documentUploadOpen"] is True
    assert [nomination["editingLocked"] for nomination in data["nominations"]] == [False]


def test_the_material_stays_open_after_registration_closes() -> None:
    """Приём кончился — файлы живут дальше, это и есть смысл отдельных сроков.

    Видео и фото раньше закрывались вместе с приёмом: номер, попавший в фестиваль в
    последний день, уже не мог заменить присланный файл.
    """
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel, CompetitionModel

    competition = CompetitionModel.objects.create(organizer_id=uuid7(), status="PUBLISHED", title="Spring", season="2025/2026")
    CategoryModel.objects.create(
        competition=competition,
        name="Vocal",
        registration_opens_at=datetime(2000, 1, 1, tzinfo=UTC),
        registration_closes_at=datetime(2001, 1, 1, tzinfo=UTC),
    )

    data = APIClient().get(_url(str(competition.id))).data["data"]

    assert data["registrationOpen"] is False
    assert data["mediaUploadOpen"] is True
    assert data["musicUploadOpen"] is True


def test_the_organizer_s_freeze_shows_on_the_genre_it_was_thrown_on() -> None:
    """Замок — жанровый, и проекция говорит это жанром, а не фестивалем.

    Сроки загрузки при этом остаются фестивальными и открытыми: они одни на все
    жанры, и свернуть в них замок вокала значило бы закрыть загрузку хореографии.
    Складывает два ответа кабинет — он знает, про какой номер спрашивает.
    """
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel

    competition_id = _seed_competition(waitlisted_nomination=True)
    CategoryModel.objects.filter(competition_id=competition_id, name="Vocal").update(editing_locked_at=datetime(2026, 5, 1, tzinfo=UTC))

    data = APIClient().get(_url(competition_id)).data["data"]

    frozen = {nomination["name"]: nomination for nomination in data["nominations"]}
    assert frozen["Vocal"]["editingLocked"] is True
    assert frozen["Vocal"]["registrationOpen"] is False
    assert frozen["Choreography"]["editingLocked"] is False
    assert data["musicUploadOpen"] is True


def test_the_festival_s_door_shuts_once_every_genre_is_frozen() -> None:
    from datetime import UTC, datetime

    from apps.competitions.infrastructure.models import CategoryModel

    competition_id = _seed_competition()
    CategoryModel.objects.filter(competition_id=competition_id).update(editing_locked_at=datetime(2026, 5, 1, tzinfo=UTC))

    data = APIClient().get(_url(competition_id)).data["data"]

    assert data["registrationOpen"] is False
