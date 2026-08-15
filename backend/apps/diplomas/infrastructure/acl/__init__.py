"""ACL adapters over sibling bounded contexts for the Diplomas application."""

from __future__ import annotations

from .actor_directory import actor_label
from .award_vocabulary import awardable_degrees
from .snapshot_source import COMPETING_SUBMISSION_STATUSES, DjangoDiplomaSnapshotSource

__all__ = ["COMPETING_SUBMISSION_STATUSES", "DjangoDiplomaSnapshotSource", "actor_label", "awardable_degrees"]
