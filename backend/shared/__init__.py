"""Shared kernel: cross-context building blocks with no business logic.

Holds framework-neutral base types, the domain-event contracts, common
exceptions, utilities, and typing helpers reused by every bounded context
(ARCH-001 §14 shared_kernel). Contexts may depend on shared; shared depends
on no context.
"""
