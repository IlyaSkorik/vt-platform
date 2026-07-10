"""Domain services for the Applications (Competition Submission) bounded context.

Stateless business behaviour that does not belong to a single entity or value
object (ARCH-001 §13.4). Framework-free; no Django, no persistence.

**No domain service is required by this iteration.** All behaviour fits naturally
on the :class:`~apps.applications.domain.entities.Submission` aggregate root, which
is the single consistency boundary. The one cross-context concern - reading
Competition configuration to validate a submission - is deliberately *not* a
domain service here: it is an outbound port (an anti-corruption gateway) declared
in :mod:`apps.applications.application.interfaces`, whose result is passed into
``Submission.submit`` as a read-model value object. Keeping it a port, not a
domain service, preserves the domain's purity (no IO) and the contexts'
independence.

This module remains as a structural placeholder so the context mirrors its
siblings.
"""

from __future__ import annotations
