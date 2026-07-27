"""ACL adapters over sibling bounded contexts for the Diplomas application."""

from __future__ import annotations

from .snapshot_source import COMPETING_SUBMISSION_STATUSES, DjangoDiplomaSnapshotSource

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoDiplomaSnapshotSource"]
