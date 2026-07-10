"""Business policies for the Applications (Competition Submission) bounded context.

Explicit, testable business rules expressed as immutable, injectable policies
(ARCH-001 §4.2, §13.4) - the seam through which behaviour extends without editing
core rules.

**No injectable policy is required by this iteration.** The Submission's
invariants are *structural* (a performance exists, at least one participant
exists, an immutable price snapshot exists, no duplicate participants/attachments,
legal status transitions only) and live on the aggregate root itself
(``Submission._assert_submittable`` / ``Submission._transition_to``). The one rule
that depends on foreign data - matching the participant count to the configured
participant group - is validated against a read-model value object
(``SubmissionParticipationPolicy``) supplied to ``Submission.submit``, so it needs
no injectable policy object either.

Anticipated future policies (the extension point): a ``ParticipantEligibilityPolicy``
(age must fall in the chosen age category), a ``RequiredAttachmentsPolicy`` (which
attachment types a competition mandates), or a ``ResubmissionPolicy`` (how many
correction rounds are allowed). Each would be a frozen, slotted dataclass injected
at the composition root.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only.
"""

from __future__ import annotations
