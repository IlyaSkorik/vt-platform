"""The operator's load-test harness for diploma generation.

Why it lives here, in the platform console's presentation layer: seeding a run
touches Competitions, Applications and Diplomas at once, and generation is then
driven through the Diplomas context's own public entry point. That is the same
pragmatic seam :mod:`read_models` documents — a tool that spans several contexts,
kept where its coupling is visible rather than smuggled into a domain that would
then have to know about all of them. Nothing here is business behaviour; it is a
rig for measuring the one that already exists.

Two properties make it safe to point at a live deployment:

* **A run never touches the real numbering.** Diploma numbers are permanent and
  the counter is scoped by the competition's *year*, so the seeded competition is
  dated in :data:`SANDBOX_YEAR` and consumes its own ``VT-2999-…`` series. Burning
  ``VT-2026-000123`` on a load test would take it from a real participant forever.
* **Everything a run creates is recoverable.** The competition carries
  :data:`MARKER` in its settings JSON, which is what :func:`cleanup` deletes by —
  including the rendered PDFs and archives in storage, which is where the actual
  disk cost of a 500-diploma run sits.

Generation itself is deliberately *not* reimplemented: :func:`start_run` calls the
same ``start_print_package`` the organizer's own button calls, so a measurement
here is a measurement of production and not of a parallel code path.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from django.core.files.storage import default_storage
from django.db.models import Count
from django.utils import timezone

from apps.applications.domain.value_objects import SubmissionStatus
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
)
from apps.diplomas.infrastructure.models import (
    AssignmentModel,
    DiplomaModel,
    DiplomaNumberSequenceModel,
    DocumentTypeChoices,
    GenerationRunModel,
    PrintJobModel,
    PrintJobStatusChoices,
    TemplateDocumentModel,
    TemplateModel,
)
from apps.diplomas.infrastructure.pdf.workspace import storage_key_of
from apps.participants.infrastructure.models.registry import (
    EducationalOrganizationModel,
    ParticipantOrganizationMembershipModel,
    ParticipantRegistryModel,
)

__all__ = [
    "MARKER",
    "MAX_COUNT",
    "SANDBOX_YEAR",
    "LoadTestTemplateUnavailableError",
    "cleanup",
    "list_runs",
    "printable_templates",
    "seed_run",
    "start_run",
]

#: Written into the seeded competition's ``settings`` JSON, and the only thing
#: :func:`cleanup` trusts — a title prefix is editable from the admin, this is not
#: shown anywhere and cannot be reached by accident.
MARKER = "print-package-loadtest"

#: The year the seeded competition is held in, and therefore the numbering scope
#: its diplomas consume. Far outside any real season (see the module docstring).
SANDBOX_YEAR = 2999

#: The largest run the console will seed in one request. Seeding is a bulk insert
#: and fast, but the *generation* it triggers is one long task in one worker, and
#: past this the honest way to test is to change the worker rather than the tirage.
MAX_COUNT = 2000


class LoadTestTemplateUnavailableError(Exception):
    """No usable diploma template — nothing to print over."""


def printable_templates() -> list[dict[str, Any]]:
    """Diploma templates a run can actually print over: assigned a PDF, not deleted.

    A template with no uploaded document is exactly what generation refuses, so
    offering one in the console's picker would only produce a failed job.
    """
    with_pdf = TemplateDocumentModel.objects.filter(deleted_at__isnull=True, template__deleted_at__isnull=True).values_list("template_id", flat=True)
    rows = TemplateModel.objects.filter(
        id__in=list(with_pdf),
        deleted_at__isnull=True,
        type=DocumentTypeChoices.DIPLOMA,
    ).order_by("name")
    return [{"id": str(row.id), "name": row.name} for row in rows]


def resolve_template(template_id: str | None) -> uuid.UUID:
    """The requested template, or any printable one. Raises if there is none."""
    available = printable_templates()
    if not available:
        raise LoadTestTemplateUnavailableError("Нет ни одного шаблона диплома с загруженным PDF — загрузите шаблон перед тестом.")
    if template_id:
        wanted = str(template_id)
        if not any(row["id"] == wanted for row in available):
            raise LoadTestTemplateUnavailableError("Выбранный шаблон не найден или у него нет загруженного PDF.")
        return uuid.UUID(wanted)
    return uuid.UUID(available[0]["id"])


def seed_run(*, count: int, nominations: int, template_id: uuid.UUID) -> tuple[CompetitionModel, list[str]]:
    """Create the synthetic competition, its taxonomy, its entries and assignments.

    None of the surrounding rows are decoration — they are what the snapshot builder
    goes looking for on **every** entry, and an entry that leaves them blank skips
    the queries a real run makes and flatters the measurement. The four taxonomy ids
    each cost a name lookup; the registry participant costs a membership join to find
    the organization printed on the diploma.

    Between them they also fill every binding a diploma template can carry, so the
    rendered pages come out looking like the real thing rather than a page of blanks
    — the one exception being the award degree, which is genuinely absent from a
    print-package copy because the ceremony has not happened yet.
    """
    stamp = timezone.now().strftime("%d.%m.%Y %H:%M")
    competition = CompetitionModel.objects.create(
        title=f"[НАГРУЗОЧНЫЙ ТЕСТ {stamp}] Генерация дипломов",
        season=str(SANDBOX_YEAR),
        organizer_id=uuid.uuid4(),
        status="PUBLISHED",
        venue_name="Тестовый зал",
        # Dated in the sandbox year — this is what keeps the run off the real
        # numbering counter (see the module docstring).
        competition_start=date(SANDBOX_YEAR, 6, 1),
        competition_end=date(SANDBOX_YEAR, 6, 3),
        settings={"load_test": MARKER},
    )

    group = ParticipantGroupModel.objects.create(competition=competition, name="Соло", min_count=1, max_count=1)
    age = AgeCategoryModel.objects.create(
        competition=competition,
        participant_group_id=group.id,
        name="10–12 лет",
        min_age=10,
        max_age=12,
    )
    categories = [
        CategoryModel.objects.create(competition=competition, name=f"Нагрузочная номинация {index + 1}", sort_order=index)
        for index in range(nominations)
    ]
    disciplines = [
        DisciplineModel.objects.create(competition=competition, category_id=category.id, name=f"Дисциплина {index + 1}")
        for index, category in enumerate(categories)
    ]

    # The registry side. A diploma prints the participant's *organization*, and the
    # snapshot reaches it through the registry entry the submission points at — so
    # without these rows that field prints nothing and its lookup never runs. Owned
    # by the competition's own (throwaway) organizer id, which is how cleanup finds
    # them again: the registry has no competition to scope by.
    school = EducationalOrganizationModel.objects.create(
        owner_id=competition.organizer_id,
        name=f"Тестовая школа искусств {stamp}",
        organization_type="school",
        city="Тестовый город",
    )
    registry = [
        ParticipantRegistryModel(
            owner_id=competition.organizer_id,
            first_name=f"Участник{index + 1:04d}",
            last_name="Нагрузочный",
            birth_date=date(2014, 5, 17),
            gender="other",
        )
        for index in range(count)
    ]
    ParticipantRegistryModel.objects.bulk_create(registry, batch_size=500)
    ParticipantOrganizationMembershipModel.objects.bulk_create(
        [ParticipantOrganizationMembershipModel(participant=entry, organization=school, is_primary=True) for entry in registry],
        batch_size=500,
    )

    submissions = []
    for index in range(count):
        slot = index % nominations
        submissions.append(
            SubmissionModel(
                competition_id=competition.id,
                applicant_id=uuid.uuid4(),
                status=SubmissionStatus.ACCEPTED.value,
                performance={
                    "title": f"Номер {index + 1:04d}",
                    "nomination_id": str(categories[slot].id),
                    "discipline_id": str(disciplines[slot].id),
                    "participant_group_id": str(group.id),
                    "age_category_id": str(age.id),
                },
                participants=[
                    {
                        "display_name": f"Нагрузочный Участник{index + 1:04d}",
                        "birth_date": "2014-05-17",
                        "registry_participant_id": str(registry[index].id),
                    }
                ],
                teachers=[{"last_name": "Педагогов", "first_name": f"Педагог{index % 37}", "role": "Преподаватель"}],
            )
        )
    SubmissionModel.objects.bulk_create(submissions, batch_size=500)

    AssignmentModel.objects.bulk_create(
        [
            AssignmentModel(
                competition_id=competition.id,
                category_id=category.id,
                template_id=template_id,
                document_type=DocumentTypeChoices.DIPLOMA,
            )
            for category in categories
        ]
    )
    return competition, [str(category.id) for category in categories]


def start_run(
    *,
    count: int,
    nominations: int,
    template_id: str | None,
    split: bool,
    force: bool,
    actor_id: uuid.UUID | None,
    actor_label: str,
) -> dict[str, Any]:
    """Seed a run and enqueue it down the organizer's own generation path.

    ``split`` enqueues one job per nomination instead of one job for the whole
    competition. The two measure different things: one job is the throughput of a
    single worker process, several at once is what the queue does when the workers
    are outnumbered — which is the case that actually delays a real festival.
    """
    from apps.diplomas.presentation.api.v1.diplomas import print_package

    resolved = resolve_template(template_id)
    competition, category_ids = seed_run(count=count, nominations=nominations, template_id=resolved)

    selections = [[category_id] for category_id in category_ids] if split else [[]]
    for selection in selections:
        print_package.start_print_package(
            competition_id=competition.id,
            category_ids=selection,
            force=force,
            actor_id=actor_id,
            actor_label=actor_label,
        )
    return _run_data(competition)


def list_runs() -> list[dict[str, Any]]:
    """Every load-test run, newest first, with the state of its generation jobs."""
    competitions = CompetitionModel.objects.filter(settings__load_test=MARKER).order_by("-created_at")
    return [_run_data(competition) for competition in competitions]


def _run_data(competition: CompetitionModel) -> dict[str, Any]:
    """One run: what was seeded, what generation has done with it so far."""
    jobs = list(PrintJobModel.objects.filter(competition_id=competition.id).order_by("created_at"))
    entries = SubmissionModel.objects.filter(competition_id=competition.id, deleted_at__isnull=True).count()
    nominations = CategoryModel.objects.filter(competition_id=competition.id, deleted_at__isnull=True).count()
    diplomas = DiplomaModel.objects.filter(competition_id=competition.id, deleted_at__isnull=True)
    rendered = diplomas.exclude(print_pdf_path="").count()

    statuses = {job.status for job in jobs}
    if not jobs:
        status = "PENDING"
    elif PrintJobStatusChoices.FAILED in statuses:
        status = "FAILED"
    elif statuses <= {PrintJobStatusChoices.COMPLETED}:
        status = "COMPLETED"
    elif PrintJobStatusChoices.RUNNING in statuses:
        status = "RUNNING"
    else:
        status = "PENDING"

    # Wall clock from the first enqueue to the last update: the number the operator
    # came for. While a job is still running it reads as elapsed-so-far, which is
    # what a progress line should say.
    started = min((job.created_at for job in jobs), default=None)
    finished = max((job.updated_at for job in jobs), default=None)
    if started is None:
        elapsed = None
    else:
        end = finished if status in {"COMPLETED", "FAILED"} and finished is not None else timezone.now()
        elapsed = max(0.0, (end - started).total_seconds())

    return {
        "competitionId": str(competition.id),
        "title": competition.title,
        "createdAt": competition.created_at,
        "entries": entries,
        "nominations": nominations,
        "diplomas": diplomas.count(),
        "rendered": rendered,
        "status": status,
        "elapsedSeconds": elapsed,
        # Per-diploma cost is the figure that scales to a real festival; only
        # meaningful once something has actually been rendered.
        "msPerDiploma": round(elapsed * 1000 / rendered) if elapsed and rendered else None,
        "jobs": [
            {
                "jobId": str(job.id),
                "status": job.status,
                "created": job.created_count,
                "skipped": job.skipped_count,
                "zipUrl": job.zip_path or None,
                "error": job.error or None,
            }
            for job in jobs
        ],
    }


def cleanup(*, competition_id: str | None = None) -> dict[str, int]:
    """Delete load-test runs — their rows *and* the files they wrote.

    Hard deletes, not the soft delete the application uses: this data was never
    real, and leaving tombstones behind would keep inflating the tables the next
    run measures against. Scoped to one run when asked, otherwise all of them.

    Files first, then rows: the references live on the rows, so deleting those
    first would strand every rendered PDF in storage with no way left to find it.
    """
    runs = CompetitionModel.objects.filter(settings__load_test=MARKER)
    if competition_id is not None:
        runs = runs.filter(id=competition_id)
    # The organizer ids are read *before* the competitions go: they are the only
    # handle on the registry rows a run created, and the registry has no competition
    # column to find them by afterwards.
    seeded = list(runs.values_list("id", "organizer_id"))
    if not seeded:
        return {"runs": 0, "files": 0, "diplomas": 0, "entries": 0}
    competition_ids = [row[0] for row in seeded]
    owner_ids = [row[1] for row in seeded]

    diplomas = DiplomaModel.objects.filter(competition_id__in=competition_ids)
    references: list[str] = []
    references += list(diplomas.exclude(print_pdf_path="").values_list("print_pdf_path", flat=True))
    references += list(diplomas.exclude(official_pdf_path="").values_list("official_pdf_path", flat=True))
    references += list(PrintJobModel.objects.filter(competition_id__in=competition_ids).exclude(zip_path="").values_list("zip_path", flat=True))
    references += list(GenerationRunModel.objects.filter(competition_id__in=competition_ids).exclude(zip_path="").values_list("zip_path", flat=True))

    removed_files = 0
    for reference in references:
        key = storage_key_of(reference)
        if default_storage.exists(key):
            default_storage.delete(key)
            removed_files += 1

    removed_diplomas = diplomas.delete()[0]
    PrintJobModel.objects.filter(competition_id__in=competition_ids).delete()
    GenerationRunModel.objects.filter(competition_id__in=competition_ids).delete()
    AssignmentModel.objects.filter(competition_id__in=competition_ids).delete()
    removed_entries = SubmissionModel.objects.filter(competition_id__in=competition_ids).delete()[0]
    # Taxonomy rows cascade from the competition; memberships cascade from the
    # registry entry, so only the two owned tables need naming.
    CompetitionModel.objects.filter(id__in=competition_ids).delete()
    ParticipantRegistryModel.objects.filter(owner_id__in=owner_ids).delete()
    EducationalOrganizationModel.objects.filter(owner_id__in=owner_ids).delete()

    # The sandbox counter too, but only once nothing is left that it numbered:
    # dropping it while another run is mid-flight would hand out numbers it has
    # already issued.
    if not CompetitionModel.objects.filter(settings__load_test=MARKER).exists():
        DiplomaNumberSequenceModel.objects.filter(scope=str(SANDBOX_YEAR)).delete()

    return {
        "runs": len(competition_ids),
        "files": removed_files,
        "diplomas": removed_diplomas,
        "entries": removed_entries,
    }


def sandbox_counts() -> dict[str, int]:
    """A quick tally the console shows above the table, so leftovers are visible."""
    competition_ids = list(CompetitionModel.objects.filter(settings__load_test=MARKER).values_list("id", flat=True))
    aggregate = SubmissionModel.objects.filter(competition_id__in=competition_ids).aggregate(entries=Count("id"))
    return {
        "runs": len(competition_ids),
        "entries": aggregate["entries"] or 0,
        "diplomas": DiplomaModel.objects.filter(competition_id__in=competition_ids).count(),
    }
