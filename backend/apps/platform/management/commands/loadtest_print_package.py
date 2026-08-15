"""``loadtest_print_package`` — measure a full diploma print run, from the shell.

The console at ``/platform/testing`` drives the same harness
(:mod:`apps.platform.presentation.api.v1.loadtest`) and is the better place to
start a run and clean up after it. This command exists for the one thing a browser
cannot give: the **in-process breakdown** — how much of the wall clock went to
building snapshots, rendering PDFs, writing them to storage and zipping them up,
plus the SQL count and peak memory behind it. That is what tells you *why* a run
is slow, rather than that it is.

A print package is one Celery task that renders every diploma in a loop, not one
task per diploma, so "500 at once" is a single long-running job. What matters is
therefore whether that loop fits inside the worker's ``--time-limit``, which the
report closes with.

Usage::

    # 500 diplomas across 5 nominations, in this process, with the breakdown
    python manage.py loadtest_print_package --count 500 --nominations 5

    # through the real queue instead (Redis → worker), polling the job
    python manage.py loadtest_print_package --count 500 --mode celery

    # queue pressure: one job per nomination, all enqueued at once
    python manage.py loadtest_print_package --count 500 --nominations 8 --mode celery --split

    # remove every load-test run and the files it wrote
    python manage.py loadtest_print_package --cleanup
"""

from __future__ import annotations

import resource
import time
import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.diplomas.application.batch_services import DiplomaBatchGenerationService, NominationTarget
from apps.diplomas.application.numbering import DiplomaNumberService
from apps.diplomas.infrastructure.acl import DjangoDiplomaSnapshotSource, awardable_degrees
from apps.diplomas.infrastructure.models import AssignmentModel, DocumentTypeChoices, PrintJobModel, PrintJobStatusChoices
from apps.diplomas.infrastructure.pdf.workspace import DjangoPrintPackageWorkspace
from apps.diplomas.infrastructure.repositories import (
    DjangoDiplomaNumberSequence,
    DjangoDiplomaRepository,
)
from apps.platform.presentation.api.v1 import loadtest

#: How often the ``celery`` mode asks the database whether the job finished.
_POLL_SECONDS = 2.0

#: The job columns the ``celery`` mode polls and then reports from — one field list
#: so the poll and the summary read the same row shape.
_JOB_FIELDS = ("id", "status", "created_count", "skipped_count", "zip_path", "error")


class _TimedSnapshots:
    """Snapshot source that records how long building each snapshot took."""

    def __init__(self, inner: DjangoDiplomaSnapshotSource) -> None:
        self._inner = inner
        self.build_seconds = 0.0
        self.builds = 0

    def list_submission_ids(self, competition_id: uuid.UUID, *, category_id: uuid.UUID | None = None) -> list[uuid.UUID]:
        return self._inner.list_submission_ids(competition_id, category_id=category_id)

    def build(self, submission_id: uuid.UUID) -> Any:
        started = time.perf_counter()
        try:
            return self._inner.build(submission_id)
        finally:
            self.build_seconds += time.perf_counter() - started
            self.builds += 1


class _TimedWorkspace:
    """Workspace that records render / store / ZIP time and the bytes produced.

    Wraps rather than subclasses so the real adapter stays exactly the code that
    runs in production — a benchmark that measures a modified renderer measures
    nothing.
    """

    def __init__(self, inner: DjangoPrintPackageWorkspace) -> None:
        self._inner = inner
        self.render_seconds = 0.0
        self.renders = 0
        self.rendered_bytes = 0
        self.store_seconds = 0.0
        self.zip_seconds = 0.0

    def load_template(self, template_id: uuid.UUID) -> Any:
        return self._inner.load_template(template_id)

    def render(self, **kwargs: Any) -> bytes:
        started = time.perf_counter()
        data = self._inner.render(**kwargs)
        self.render_seconds += time.perf_counter() - started
        self.renders += 1
        self.rendered_bytes += len(data)
        return data

    def render_place_sheet(self, **kwargs: Any) -> bytes | None:
        # Counted with the diplomas: a place sheet is the same drawing code over a
        # blank page, and there are a handful of them against a whole tirage.
        started = time.perf_counter()
        data = self._inner.render_place_sheet(**kwargs)
        self.render_seconds += time.perf_counter() - started
        if data is not None:
            self.renders += 1
            self.rendered_bytes += len(data)
        return data

    def store_pdf(self, **kwargs: Any) -> str:
        started = time.perf_counter()
        try:
            return self._inner.store_pdf(**kwargs)
        finally:
            self.store_seconds += time.perf_counter() - started

    def store_zip(self, **kwargs: Any) -> str:
        started = time.perf_counter()
        try:
            return self._inner.store_zip(**kwargs)
        finally:
            self.zip_seconds += time.perf_counter() - started


class Command(BaseCommand):
    """Seed a synthetic competition and measure a full print-package generation."""

    help = "Load-test diploma generation: seed N entries, run the print package, report timings."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--count", type=int, default=300, help="How many entries to seed (default 300).")
        parser.add_argument("--nominations", type=int, default=5, help="How many nominations to spread them over (default 5).")
        parser.add_argument(
            "--template",
            default=None,
            help="Template id to print over. Defaults to any diploma template that has an uploaded PDF.",
        )
        parser.add_argument(
            "--mode",
            choices=("sync", "celery"),
            default="sync",
            help="sync: run in this process with a per-stage breakdown. celery: enqueue the real task and poll.",
        )
        parser.add_argument(
            "--split",
            action="store_true",
            help="celery mode only: enqueue one job per nomination at once, to load the queue rather than one worker.",
        )
        parser.add_argument("--force", action="store_true", help="Re-render print PDFs that already exist.")
        parser.add_argument("--cleanup", action="store_true", help="Delete every load-test run and its files, then exit.")
        parser.add_argument("--timeout", type=int, default=3600, help="celery mode: seconds to wait for the job (default 3600).")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["cleanup"]:
            removed = loadtest.cleanup()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removed {removed['runs']} run(s): {removed['entries']} entries, {removed['diplomas']} diplomas, {removed['files']} file(s)."
                )
            )
            return

        count = int(options["count"])
        nominations = max(1, int(options["nominations"]))
        if count < 1:
            raise CommandError("--count must be at least 1.")

        try:
            template_id = loadtest.resolve_template(options["template"])
        except loadtest.LoadTestTemplateUnavailableError as exc:
            raise CommandError(str(exc)) from exc

        if options["mode"] == "celery":
            self._run_celery(
                count=count,
                nominations=nominations,
                template_id=str(template_id),
                force=bool(options["force"]),
                split=bool(options["split"]),
                timeout=int(options["timeout"]),
            )
        else:
            competition, category_ids = loadtest.seed_run(count=count, nominations=nominations, template_id=template_id)
            self.stdout.write(
                self.style.SUCCESS(f"Seeded {competition.id} — {count} entries over {nominations} nomination(s), template {template_id}.")
            )
            self._run_sync(competition_id=competition.id, category_ids=category_ids, force=bool(options["force"]))

        self.stdout.write("")
        self.stdout.write("Data kept. Remove it with: python manage.py loadtest_print_package --cleanup")

    # --- runs -------------------------------------------------------------

    def _run_sync(self, *, competition_id: uuid.UUID, category_ids: list[str], force: bool) -> None:
        """Render the whole package in this process, timing each stage."""
        snapshots = _TimedSnapshots(DjangoDiplomaSnapshotSource())
        workspace = _TimedWorkspace(DjangoPrintPackageWorkspace())
        service = DiplomaBatchGenerationService(
            repository=DjangoDiplomaRepository(),
            snapshots=snapshots,  # type: ignore[arg-type]  # duck-typed timing proxy
            workspace=workspace,  # type: ignore[arg-type]
            numbers=DiplomaNumberService(sequence=DjangoDiplomaNumberSequence()),
            place_degrees=awardable_degrees(),
        )
        targets = [NominationTarget(category_id=uuid.UUID(cid), template_id=self._template_of(competition_id, cid)) for cid in category_ids]

        rss_before = _peak_rss_mb()
        self.stdout.write("Generating in-process…")
        started = time.perf_counter()
        with CaptureQueriesContext(connection) as queries:
            result = service.generate_print_package(
                competition_id=competition_id,
                targets=targets,
                now=timezone.now(),
                force=force,
            )
        elapsed = time.perf_counter() - started

        total = result.created + result.skipped
        per_item = elapsed / total if total else 0.0
        untracked = elapsed - snapshots.build_seconds - workspace.render_seconds - workspace.store_seconds - workspace.zip_seconds

        def stage(seconds: float) -> str:
            return f"{seconds:6.1f} s  ({_share(seconds, elapsed)})"

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== print package: in-process ==="))
        self._row("diplomas", f"{total} ({result.created} created, {result.skipped} skipped)")
        self._row("wall time", f"{elapsed:.1f} s   ({per_item * 1000:.0f} ms per diploma)")
        self._row("throughput", f"{total / elapsed:.1f} diplomas/s" if elapsed else "n/a")
        self.stdout.write("  ---- where the time went ----")
        self._row("snapshot build", f"{stage(snapshots.build_seconds)}  {snapshots.builds} builds")
        self._row("pdf render", f"{stage(workspace.render_seconds)}  {workspace.renders} renders")
        self._row("store pdf", stage(workspace.store_seconds))
        self._row("build zip", stage(workspace.zip_seconds))
        self._row("repository + rest", stage(untracked))
        self.stdout.write("  ---- cost ----")
        rendered_mb = workspace.rendered_bytes / 1024 / 1024
        self._row("rendered bytes", f"{rendered_mb:.1f} MB  ({_avg_kb(workspace.rendered_bytes, workspace.renders)} per pdf)")
        self._row("sql queries", f"{len(queries)}  ({len(queries) / total:.1f} per diploma)" if total else str(len(queries)))
        self._row("peak rss", f"{_peak_rss_mb():.0f} MB  (was {rss_before:.0f} MB before the run)")
        self._row("zip", result.zip_path)
        self._verdict(elapsed, total)

    def _run_celery(self, *, count: int, nominations: int, template_id: str, force: bool, split: bool, timeout: int) -> None:
        """Enqueue through the real path and poll the durable job rows.

        This is the honest end-to-end number: it includes the broker hop, the
        worker's own process, and whatever else that worker is busy with.
        """
        started = time.perf_counter()
        run = loadtest.start_run(
            count=count,
            nominations=nominations,
            template_id=template_id,
            split=split,
            force=force,
            actor_id=None,
            actor_label="loadtest (cli)",
        )
        job_ids = [uuid.UUID(job["jobId"]) for job in run["jobs"]]
        self.stdout.write(self.style.SUCCESS(f"Seeded {run['competitionId']} — {count} entries, {len(job_ids)} job(s) enqueued."))

        terminal = {PrintJobStatusChoices.COMPLETED, PrintJobStatusChoices.FAILED}
        deadline = started + timeout
        seen_running = False
        while time.perf_counter() < deadline:
            rows = list(PrintJobModel.objects.filter(id__in=job_ids).values(*_JOB_FIELDS))
            if not seen_running and any(row["status"] == PrintJobStatusChoices.RUNNING for row in rows):
                self.stdout.write(f"  picked up by a worker after {time.perf_counter() - started:.1f} s")
                seen_running = True
            if all(row["status"] in terminal for row in rows):
                break
            time.sleep(_POLL_SECONDS)
        else:
            self.stdout.write(self.style.ERROR(f"Timed out after {timeout} s — jobs still running. Inspect: {[str(i) for i in job_ids]}"))
            return

        elapsed = time.perf_counter() - started
        rows = list(PrintJobModel.objects.filter(id__in=job_ids).values(*_JOB_FIELDS))
        total = sum(row["created_count"] + row["skipped_count"] for row in rows)
        failed = [row for row in rows if row["status"] == PrintJobStatusChoices.FAILED]

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== print package: through Celery ==="))
        self._row("jobs", f"{len(rows)} ({len(failed)} failed)")
        self._row("diplomas", str(total))
        self._row("wall time", f"{elapsed:.1f} s   ({elapsed / total * 1000:.0f} ms per diploma)" if total else f"{elapsed:.1f} s")
        for row in rows:
            note = row["error"] or row["zip_path"]
            self.stdout.write(f"    {row['id']}  {row['status']:9}  {row['created_count'] + row['skipped_count']:4} docs  {note}")
        if not failed:
            self._verdict(elapsed, total)

    def _verdict(self, elapsed: float, total: int) -> None:
        """Read the measurement against the worker's own hard limits."""
        if not total:
            return
        per_item = elapsed / total
        self.stdout.write("  ---- headroom ----")
        for tirage in (500, 1000, 3000):
            projected = per_item * tirage
            fits = "ok" if projected < 3300 else ("SOFT LIMIT" if projected < 3600 else "OVER --time-limit")
            self.stdout.write(f"  {tirage:5} diplomas ≈ {projected / 60:5.1f} min   {fits}")
        self.stdout.write("  (worker runs --soft-time-limit 3300 / --time-limit 3600; a job over the hard limit is killed mid-run)")

    def _row(self, label: str, value: str) -> None:
        self.stdout.write(f"  {label:<18}{value}")

    def _template_of(self, competition_id: uuid.UUID, category_id: str) -> uuid.UUID:
        assignment = (
            AssignmentModel.objects.filter(
                competition_id=competition_id,
                category_id=category_id,
                document_type=DocumentTypeChoices.DIPLOMA,
                deleted_at__isnull=True,
            )
            .values_list("template_id", flat=True)
            .first()
        )
        if assignment is None:  # pragma: no cover - seeded a moment ago
            raise CommandError(f"No diploma assignment for nomination {category_id}.")
        return uuid.UUID(str(assignment))


def _share(part: float, whole: float) -> str:
    return f"{part / whole * 100:4.1f}%" if whole else "  n/a"


def _avg_kb(total_bytes: int, count: int) -> str:
    return f"{total_bytes / count / 1024:.0f} KB" if count else "n/a"


def _peak_rss_mb() -> float:
    """Peak resident set size of this process, in MB (Linux reports KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
