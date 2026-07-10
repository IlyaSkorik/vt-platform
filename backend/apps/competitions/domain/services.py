"""Domain services for the Competitions bounded context.

Stateless business behaviour that does not belong to a single entity or value
object — coordination across aggregates within this context (ARCH-001 §13.4).
Framework-free; no Django, no persistence.

**No domain service is required by this iteration.** All behaviour belongs to the
single :class:`~apps.competitions.domain.entities.Competition` aggregate: even the
admissibility and pricing lookups (``Competition.is_admissible`` /
``Competition.price_for``) are queries on the root, not cross-aggregate
coordination. A domain service would earn its place only once a second aggregate
exists to coordinate with (e.g. the future Applications context querying
admissibility through a published read model).
"""

from __future__ import annotations
