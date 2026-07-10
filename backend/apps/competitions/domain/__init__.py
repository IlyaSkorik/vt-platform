"""Domain layer for the Competitions bounded context.

The framework-free business core. Two aggregate roots:

* ``Competition`` — the configurable competition, with its child entities
  (``Category``, ``Discipline``, ``AgeCategory``, ``ParticipantGroup``,
  ``CompetitionRegulation``, ``CompetitionDocument``, ``AdditionalService``) and its
  admission/pricing rule value objects.
* ``CompetitionTemplate`` — a reusable configuration blueprint cloned into new drafts.

Plus their value objects, domain events, and exceptions. No Django, no ORM, no IO
(ARCH-001 §4.1, §7.2).
"""
