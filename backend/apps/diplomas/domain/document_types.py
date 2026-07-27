"""Document types and the rules that distinguish them.

This is the extension point of the Diplomas context. A template produces exactly
one *kind* of document, and the kinds differ only in their rules — not in how they
are composed, bound, rendered or stored. Those rules live here, declared once per
type, so the generation pipeline stays type-agnostic.

Adding a third kind (say ``CERTIFICATE``) means adding a :class:`DocumentType`
member and one :class:`DocumentPolicy` entry. Nothing about templates,
assignments, competitions or nominations changes — see the module-level note in
:mod:`apps.diplomas.application.issued_documents`.

Framework-free (no Django imports).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["DIPLOMA_FIELD_TYPES", "THANK_YOU_FIELD_TYPES", "DocumentPolicy", "DocumentType", "policy_for"]

#: Every element kind a template layout can carry. Mirrors the editor's catalogue
#: and the layout serializer's whitelist.
DIPLOMA_FIELD_TYPES: frozenset[str] = frozenset(
    {
        "participant_name",
        "participant_age",
        "teacher",
        "organization",
        "nomination_block",
        "work",
        "competition_name",
        "competition_date",
        "competition_city",
        "award_degree",
        "diploma_issue_date",
        "qr_block",
        "free_text",
    }
)

#: What a thank-you letter may carry, and nothing more.
#:
#: A courtesy letter names who is being thanked, who taught them, and which event
#: it was for. It ranks nothing, so there is no degree; it is not registered, so
#: there is no number, issue date or QR; and it does not itemise the entry, so no
#: age, organization, nomination or work. Free text carries whatever wording the
#: organizer wants.
THANK_YOU_FIELD_TYPES: frozenset[str] = frozenset(
    {
        "participant_name",
        "teacher",
        "competition_name",
        "competition_date",
        "competition_city",
        "free_text",
    }
)


class DocumentType(Enum):
    """A kind of document the platform issues.

    Also the *template* type: a template is authored for one kind of document, so
    the two are one concept rather than two enums that could drift apart. The REST
    surface exposes it as a template's ``type``.
    """

    DIPLOMA = "DIPLOMA"
    THANK_YOU = "THANK_YOU"


@dataclass(frozen=True, slots=True)
class DocumentPolicy:
    """What a document kind requires, stated as data rather than as branches.

    Every flag answers a question the generation pipeline would otherwise have to
    ask with an ``if type == ...``. Kept declarative so a new kind is a new row,
    not a new code path.
    """

    document_type: DocumentType

    #: Draws a permanent number from the registry sequence (``VT-<year>-<n>``).
    numbered: bool

    #: Carries a verification token, a printed QR, and a public register entry.
    verifiable: bool

    #: Can bear a jury result, so generation may legitimately wait for one.
    awards_degree: bool

    #: **May** reach the participant the moment it is generated, with no separate
    #: publication step. A diploma may not — it is published through the registry
    #: after the ceremony — while a courtesy letter needs no such ceremony. This is
    #: permission, not obligation: the generating run decides whether to use it, so
    #: an organizer can prepare letters for printing without showing them yet.
    publishes_on_generation: bool

    #: Element kinds a template of this document kind may place.
    field_types: frozenset[str]

    #: Whether a teacher field prints roles alongside names ("Педагог: ФИО").
    #: A diploma credits a teacher in a stated capacity; a thank-you letter simply
    #: thanks a person, so it prints the name alone.
    teacher_roles: bool

    #: Whether one document is issued **per teacher** rather than one per
    #: performance. A thank-you letter is addressed to a person, so two teachers on
    #: an entry mean two separate letters — each naming only its own recipient. A
    #: diploma belongs to the performance and lists every teacher on one sheet.
    per_teacher: bool

    def allows_field(self, field_type: str) -> bool:
        """Whether this kind of document may carry that element."""
        return field_type in self.field_types

    @property
    def is_registry_document(self) -> bool:
        """Whether this kind belongs to the numbered, verifiable diploma registry.

        Such documents are owned by the ``Diploma`` aggregate; everything else is
        an :class:`~apps.diplomas.domain.issued_document.IssuedDocument`.
        """
        return self.numbered and self.verifiable


#: The rule table. One entry per :class:`DocumentType`, exhaustively.
_POLICIES: dict[DocumentType, DocumentPolicy] = {
    # The diploma: the participant's award record. Numbered for the register,
    # verifiable by QR, may carry a degree, and is published deliberately by the
    # organizer after the ceremony rather than on generation.
    DocumentType.DIPLOMA: DocumentPolicy(
        document_type=DocumentType.DIPLOMA,
        numbered=True,
        verifiable=True,
        awards_degree=True,
        publishes_on_generation=False,
        field_types=DIPLOMA_FIELD_TYPES,
        teacher_roles=True,
        per_teacher=False,
    ),
    # The thank-you letter: a courtesy, not an award. Nothing to rank, nothing to
    # verify, nothing to number — so it can reach the participant immediately.
    DocumentType.THANK_YOU: DocumentPolicy(
        document_type=DocumentType.THANK_YOU,
        numbered=False,
        verifiable=False,
        awards_degree=False,
        publishes_on_generation=True,
        field_types=THANK_YOU_FIELD_TYPES,
        teacher_roles=False,
        per_teacher=True,
    ),
}


def policy_for(document_type: DocumentType) -> DocumentPolicy:
    """The rules for a document kind.

    Raises :class:`KeyError` for a kind with no policy — deliberately loud, so a
    new :class:`DocumentType` member cannot be added without also declaring how it
    behaves.
    """
    return _POLICIES[document_type]
