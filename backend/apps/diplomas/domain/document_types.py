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

__all__ = ["DocumentPolicy", "DocumentType", "policy_for"]


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

    #: Reaches the participant the moment it is generated, with no separate
    #: publication step by the organizer.
    publishes_on_generation: bool

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
    ),
    # The thank-you letter: a courtesy, not an award. Nothing to rank, nothing to
    # verify, nothing to number — so it can reach the participant immediately.
    DocumentType.THANK_YOU: DocumentPolicy(
        document_type=DocumentType.THANK_YOU,
        numbered=False,
        verifiable=False,
        awards_degree=False,
        publishes_on_generation=True,
    ),
}


def policy_for(document_type: DocumentType) -> DocumentPolicy:
    """The rules for a document kind.

    Raises :class:`KeyError` for a kind with no policy — deliberately loud, so a
    new :class:`DocumentType` member cannot be added without also declaring how it
    behaves.
    """
    return _POLICIES[document_type]
