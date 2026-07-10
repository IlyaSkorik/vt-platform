"""Ports (abstract interfaces) for the Competitions bounded context.

Following the layering of the Identity and Organization contexts, the outbound
**application ports** (repository and gateway protocols the use cases depend on)
live in :mod:`apps.competitions.application.interfaces`, not here — that is where
:class:`~apps.competitions.application.interfaces.CompetitionRepository` and the
ambient ``Clock`` / ``UuidGenerator`` / ``EventPublisher`` seams are defined.

This module is intentionally empty: the domain layer defines no ports of its own
(no domain-service interface is required this iteration). It remains as a
structural placeholder so the context mirrors its siblings.
"""

from __future__ import annotations
