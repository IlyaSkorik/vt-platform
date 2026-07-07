"""Application-layer exceptions for the Participants bounded context.

Purpose
    The application layer speaks its **own** error vocabulary. Use cases will
    catch the typed domain errors raised by value objects, policies, and this
    context's aggregates and re-raise them as application errors, so callers (the
    REST edge, a CLI, a task) depend only on application-level meaning — never on
    the domain's internal exception tree (ARCH-001 §7.6).

Layer responsibility
    Translation and framing of errors for use-case callers. Two rules apply:
    **never swallow** — translations preserve the original domain error as the
    cause (``raise ... from exc``), and faults that signal a programming/
    composition mistake propagate unchanged; and each error carries a stable,
    machine-readable code the presentation layer maps to an RFC 9457 Problem
    Details ``type``.

Dependency rules
    Standard library only — no Django or DRF. May import this context's
    ``domain`` errors to translate them; must not import ``infrastructure`` or
    ``presentation``.

Structure only at bootstrap — no exception types defined yet.
"""
