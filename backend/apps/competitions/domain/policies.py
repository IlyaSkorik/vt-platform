"""Business policies for the Competitions bounded context.

Explicit, testable business rules expressed as immutable, injectable policies
(ARCH-001 §4.2, §13.4) — the seam through which behaviour extends without editing
core rules.

**No injectable policy is required by this iteration.** The Competition's
invariants are *structural* (referential integrity between categories,
disciplines, age categories, participant groups, formats, admission and pricing
rules) rather than *tunable*, so they live on the aggregate root itself
(``Competition._validate_combination`` / ``_assert_publishable``) rather than in a
configurable policy object.

Anticipated future policies (the extension point): an ``AgeBandOverlapPolicy``
(forbid vs. allow overlapping age categories), a ``PricingCoveragePolicy`` (which
admissible combinations must be priced before publication), or a
``RegistrationWindowPolicy`` (how the registration period must relate to the
competition period). Each would be a frozen, slotted dataclass injected at the
composition root.

**Pure domain code** (ARCH-001 §4.1, §7.2): standard library only.
"""

from __future__ import annotations
