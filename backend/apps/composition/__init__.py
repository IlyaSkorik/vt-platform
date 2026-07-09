"""Composition bounded-context edge.

This is **not** a domain — it owns no aggregates, models, or business rules. It is
the platform's composition layer: the single sanctioned place allowed to know more
than one bounded context, where cross-context read models are assembled into a
response no individual context should own.

Its sole endpoint today is ``GET /users/me``, which composes the authenticated
account (from Identity) with that account's staff status (from Organization) into
one payload. Neither Identity nor Organization may own this endpoint — doing so
would create a dependency edge between them (ARCH-001 §14). Composing it here keeps
both contexts independent while still presenting the client a unified view.
"""
