"""Ports (abstract interfaces) for the Applications (Competition Submission) context.

Following the layering of the Identity, Organization and Competition contexts, the
outbound **application ports** (the repository, the Competition anti-corruption
gateway, and the ambient ``Clock`` / ``UuidGenerator`` / ``EventPublisher`` seams
the use cases depend on) live in
:mod:`apps.applications.application.interfaces`, not here.

This module is intentionally empty: the domain layer defines no ports of its own
(no domain-service interface is required this iteration). It remains as a
structural placeholder so the context mirrors its siblings.
"""

from __future__ import annotations
