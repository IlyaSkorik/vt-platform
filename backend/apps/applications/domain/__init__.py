"""Domain layer for the Applications (Competition Submission) bounded context.

The framework-free business core. One aggregate root:

* ``Submission`` - one competitive performance submitted to one competition, with
  its child entities (``Participant``, ``Teacher``, ``Attachment``, ``Review``),
  its single ``Performance`` value object, and its immutable ``PriceSnapshot``.

Plus their value objects, domain events, and exceptions. No Django, no ORM, no IO
(ARCH-001 §4.1, §7.2). The Competition, Identity and Organization contexts are
referenced by id only and never imported.
"""
