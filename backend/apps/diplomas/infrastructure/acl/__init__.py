"""ACL adapters over sibling bounded contexts for the Diplomas application."""

from __future__ import annotations

from .snapshot_source import DjangoDiplomaSnapshotSource

__all__ = ["DjangoDiplomaSnapshotSource"]
