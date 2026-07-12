"""Domain layer for the Teacher Directory bounded context.

The framework-free business core. One aggregate root:

* ``Teacher`` - one reusable entry in a user's personal directory of mentors,
  owned by an ``OwnerId``, with a configurable ``TeacherRole``, optional contact
  details, and an archive lifecycle.

Plus its value objects, domain events, and exceptions. No Django, no ORM, no IO
(ARCH-001 §4.1, §7.2). The Identity context (the owner) is referenced by id only
and never imported.
"""
