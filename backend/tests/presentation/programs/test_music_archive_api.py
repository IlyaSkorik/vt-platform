"""The backing-track archive an organizer hands to the sound desk.

Driven through the real edge because the archive only exists there: the service
decides what belongs in it and under what name, but the bytes come from storage and
the ZIP is assembled in the response.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from apps.applications.infrastructure.models.submission import SubmissionModel

from .test_programs_api import _act, _create_program, outsider_client, scope, staff_client  # noqa: F401

pytestmark = pytest.mark.django_db

_PROGRAMS = "/api/v1/staff/programs"


def _stored(name: str, content: bytes = b"backing track") -> str:
    """Put a file in storage and return the reference a submission would carry."""
    return default_storage.save(f"uploads/{uuid.uuid4()}-{name}", ContentFile(content))


def _attach_music(submission_id: str, *references: str) -> None:
    submission = SubmissionModel.objects.get(id=submission_id)
    submission.attachments = [{"id": str(uuid.uuid4()), "type": "MUSIC", "file": reference, "caption": None} for reference in references]
    submission.save(update_fields=["attachments"])


def _filled_program(client: APIClient, competition_scope: tuple[str, str], **overrides: Any) -> str:
    program_id = _create_program(client, competition_scope, **overrides)["id"]
    filled = client.post(f"{_PROGRAMS}/{program_id}/items/fill", {}, format="json")
    assert filled.status_code in (200, 201), filled.data
    return str(program_id)


def _archive(response: Any) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))


class TestMusicArchive:
    def test_the_archive_carries_one_track_per_number(self, staff_client: APIClient, scope: tuple[str, str]) -> None:  # noqa: F811
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200, performer="Иванова Анна")
        _attach_music(submission_id, _stored("track.mp3"))
        program_id = _filled_program(staff_client, scope)

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/music.zip")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        with _archive(response) as archive:
            assert archive.namelist() == ["01 — Иванова Анна — Катюша.mp3"]
            assert archive.read("01 — Иванова Анна — Катюша.mp3") == b"backing track"

    def test_a_number_without_a_track_is_named_in_the_notes(self, staff_client: APIClient, scope: tuple[str, str]) -> None:  # noqa: F811
        competition_id, nomination_id = scope
        _act(competition_id=competition_id, nomination_id=nomination_id, title="Гимн", seconds=180, performer="Петров Пётр")
        program_id = _filled_program(staff_client, scope)

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/music.zip")
        assert response.status_code == 200
        with _archive(response) as archive:
            assert archive.namelist() == ["ПРОЧТИ.txt"]
            assert "Петров Пётр" in archive.read("ПРОЧТИ.txt").decode()

    def test_a_track_missing_from_storage_costs_only_itself(self, staff_client: APIClient, scope: tuple[str, str]) -> None:  # noqa: F811
        competition_id, nomination_id = scope
        present = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200, performer="Иванова Анна")
        absent = _act(competition_id=competition_id, nomination_id=nomination_id, title="Гимн", seconds=180, performer="Петров Пётр")
        _attach_music(present, _stored("track.mp3"))
        _attach_music(absent, "uploads/never-written.mp3")
        program_id = _filled_program(staff_client, scope)

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/music.zip")
        with _archive(response) as archive:
            # "Гимн" fills ahead of "Катюша", so the surviving track is number two.
            assert "02 — Иванова Анна — Катюша.mp3" in archive.namelist()
            assert "Петров Пётр" in archive.read("ПРОЧТИ.txt").decode()

    def test_two_tracks_of_the_same_name_both_survive(self, staff_client: APIClient, scope: tuple[str, str]) -> None:  # noqa: F811
        competition_id, nomination_id = scope
        submission_id = _act(competition_id=competition_id, nomination_id=nomination_id, title="Катюша", seconds=200, performer="Иванова Анна")
        _attach_music(submission_id, _stored("a.mp3", b"first"), _stored("b.mp3", b"second"))
        program_id = _filled_program(staff_client, scope)

        response = staff_client.get(f"{_PROGRAMS}/{program_id}/music.zip")
        with _archive(response) as archive:
            assert sorted(archive.namelist()) == [
                "01 — Иванова Анна — Катюша (2).mp3",
                "01 — Иванова Анна — Катюша.mp3",
            ]

    def test_a_non_staff_caller_is_refused(self, outsider_client: APIClient, scope: tuple[str, str], staff_client: APIClient) -> None:  # noqa: F811
        program_id = _filled_program(staff_client, scope)
        assert outsider_client.get(f"{_PROGRAMS}/{program_id}/music.zip").status_code == 403
