"""ORM models (adapters) for the Applications bounded context.

Django models live ONLY here, never in the domain (ARCH-001 §7.2, §14), and carry
NO business logic. Tables are named with the ``applications_`` context prefix. The
aggregates' child collections are stored as JSON on the parent row (see the model
docstrings); scalar, indexed columns carry the queryable facts.
"""

from __future__ import annotations

from .application import ApplicationModel
from .base import BasePersistenceModel, uuid7
from .submission import SubmissionModel

__all__ = ["ApplicationModel", "BasePersistenceModel", "SubmissionModel", "uuid7"]
