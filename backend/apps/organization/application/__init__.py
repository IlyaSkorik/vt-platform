"""Application layer for the Organization bounded context.

Use cases (command/query handlers) that orchestrate the domain through
application **ports** (:mod:`apps.organization.application.interfaces`). Handlers
hold no business rules (those live in the domain) and no persistence details
(those live in infrastructure). Framework-free (ARCH-001 §7.3).
"""
