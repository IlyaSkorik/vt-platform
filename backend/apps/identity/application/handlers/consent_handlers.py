"""Use cases for the consent journal.

Three writes and one read, each deliberately small: the journal has no business rules
of its own beyond "record what was accepted, never lose what was". Which consents a
given flow *requires* is decided where that flow lives — registration, the participant
registry, the application wizard — not here.

The handlers do not load the ``User`` aggregate. A consent record is about the account
but is not part of its consistency boundary: two guardians recording consent for two
children must not contend on one row, and a withdrawal must succeed even for an account
that is locked, since refusing it would be refusing a right the Law grants
unconditionally (art. 5 of Law No. 99-З).
"""

from __future__ import annotations

from apps.identity.application.commands.consent_commands import (
    AcceptConsentCommand,
    ListConsentsQuery,
    WithdrawAcceptedConsentCommand,
)
from apps.identity.application.dto import ConsentRecordDto
from apps.identity.application.interfaces import Clock, ConsentJournal

__all__ = [
    "AcceptConsentHandler",
    "ListConsentsHandler",
    "WithdrawAcceptedConsentHandler",
]


class AcceptConsentHandler:
    """Use case: record one accepted consent at the version the subject was shown."""

    def __init__(self, *, consents: ConsentJournal, clock: Clock) -> None:
        self._consents = consents
        self._clock = clock

    def handle(self, command: AcceptConsentCommand) -> ConsentRecordDto:
        return self._consents.grant(
            user_id=command.user_id,
            consent_type=command.consent_type,
            version=command.version,
            granted_at=self._clock.utcnow(),
            purpose=command.purpose,
            subject_participant_id=command.subject_participant_id,
        )


class WithdrawAcceptedConsentHandler:
    """Use case: withdraw the consent currently in force.

    Returns ``None`` when there was nothing active. That is not an error: a subject
    asking to withdraw a consent they never gave has got the outcome they wanted, and
    reporting a failure would only invite them to try again.
    """

    def __init__(self, *, consents: ConsentJournal, clock: Clock) -> None:
        self._consents = consents
        self._clock = clock

    def handle(self, command: WithdrawAcceptedConsentCommand) -> ConsentRecordDto | None:
        return self._consents.withdraw(
            user_id=command.user_id,
            consent_type=command.consent_type,
            withdrawn_at=self._clock.utcnow(),
            subject_participant_id=command.subject_participant_id,
        )


class ListConsentsHandler:
    """Query: what this account has agreed to, or its whole journal."""

    def __init__(self, *, consents: ConsentJournal) -> None:
        self._consents = consents

    def handle(self, query: ListConsentsQuery) -> tuple[ConsentRecordDto, ...]:
        return self._consents.list_for_user(user_id=query.user_id, include_history=query.include_history)
