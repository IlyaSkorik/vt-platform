"""Commands and queries for the consent journal.

Separate from :mod:`user_commands` because these do not mutate the ``User``
aggregate. The account's headline ``consent_version`` is one field on the user; the
journal is the *record set* the published policy promises — one entry per consent,
carrying the version of the text the subject actually saw (LEGAL-001 §13.3). The two
answer different questions and are written by different use cases.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AcceptConsentCommand",
    "ListConsentsQuery",
    "WithdrawAcceptedConsentCommand",
]


@dataclass(frozen=True, slots=True)
class AcceptConsentCommand:
    """Record that a subject accepted one consent, at the version they were shown.

    ``version`` is the version of the *text* — not of the platform, and not of the
    privacy policy as a whole. A consent whose wording changes gets a new version, so
    ``(consent_type, version)`` always identifies exactly what was agreed to.

    ``subject_participant_id`` is set when an adult consents on a child's behalf: the
    record then names both the person who granted it and the child it concerns, which
    is what makes a guardian's withdrawal traceable to the right participant.
    """

    user_id: str
    consent_type: str
    version: str
    purpose: str | None = None
    subject_participant_id: str | None = None


@dataclass(frozen=True, slots=True)
class WithdrawAcceptedConsentCommand:
    """Withdraw the active consent of one type, optionally for one participant.

    Withdrawal never deletes the entry — the record stands with a withdrawal
    timestamp, because the evidence that consent once existed is exactly what makes
    the processing that happened under it lawful.
    """

    user_id: str
    consent_type: str
    subject_participant_id: str | None = None


@dataclass(frozen=True, slots=True)
class ListConsentsQuery:
    """Read the journal for one account.

    Answers the subject's own question ("what have I agreed to?") and, with
    ``include_history``, the auditor's ("what did they agree to, and when did it
    change?").
    """

    user_id: str
    include_history: bool = False
