"""Domain layer for the Applications bounded context.

The framework-free business core. Two independent aggregate roots:

* ``Submission`` - one competitive performance submitted to one competition, with
  its child entities (``Participant``, ``Teacher``, ``Attachment``, ``Review``),
  its single ``Performance`` value object, and its immutable ``PriceSnapshot``.
* ``Application`` - the *order* grouping one applicant's Submissions for one
  competition. It references its Submissions by id only (caching a display
  ``SubmissionRef`` snapshot of each), owns the educational-organization
  reference, the selected additional services, the recorded consents, the
  immutable ``TotalPriceSnapshot`` and the payment state, and guards the
  order-level lifecycle. It runs no review of its own - it derives its readiness
  for payment from its submissions' cached statuses.

Plus their value objects, domain events, and exceptions. No Django, no ORM, no IO
(ARCH-001 §4.1, §7.2). The Competition, Identity, Organization and Institutions
contexts are referenced by id only and never imported.
"""
