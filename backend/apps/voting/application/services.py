"""Use cases of the Voting bounded context.

One service over one aggregate, plus the votes table beside it. Every organizer
operation loads the ballot, asks the domain to change it, saves it and renders the
result; the public ones do the same and additionally consult the votes.

The write methods return the whole rendered ballot. An editor needs the recomputed
list after every change anyway — adding a nominee renumbers the rest — so returning
it removes a follow-up request and with it any chance of rendering a stale list.

**Where the anti-fraud lives.** The aggregate answers "is this ballot open and is
this nominee votable"; this layer answers "has this person already voted, and has
this network sent an implausible amount". It has to be here, because the second
question is about the votes table and the first is about the aggregate, and only
this layer holds both.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from apps.voting.application.commands import (
    AddNomineeCommand,
    CastVoteCommand,
    CreateBallotCommand,
    EditNomineeCommand,
    ImportNomineesCommand,
    NomineeRow,
    ReorderNomineesCommand,
    SeedFromProgramCommand,
    UpdateBallotCommand,
)
from apps.voting.application.dto import (
    BallotDetailView,
    BallotSummaryView,
    ImportPreviewView,
    NomineeView,
    PublicBallotView,
    PublicNomineeView,
    VoteReceiptView,
)
from apps.voting.application.interfaces import (
    BallotRepository,
    Clock,
    NomineeCatalog,
    SlugFactory,
    UuidGenerator,
    VoteRepository,
    VoterTokens,
)
from apps.voting.domain.entities import Ballot, BallotNominee
from apps.voting.domain.exceptions import (
    BallotNotFoundError,
    InvalidBallotDataError,
    SlugUnavailableError,
    TooManyVotesFromNetworkError,
    VoteLimitReachedError,
    VotingClosedError,
)
from apps.voting.domain.value_objects import (
    BallotStatus,
    BallotTitle,
    Cooldown,
    NomineeText,
    PublicSlug,
    RevealPolicy,
    VoteLimit,
    VotingWindow,
)

__all__ = ["NETWORK_VOTE_CEILING", "BallotService"]

#: How many votes one network may send inside one repeat window before the soft
#: brake engages.
#:
#: Deliberately high. A hall, a school and a café share one address between
#: hundreds of phones, and a strict ceiling would refuse the real audience while
#: barely inconveniencing anyone determined. This catches a script running from one
#: machine, which is the thing a mild ballot is actually likely to meet.
NETWORK_VOTE_CEILING: Final = 300

#: How many attempts to mint a free slug before giving up. Collisions are
#: astronomically unlikely; the loop exists so a failure is an error rather than
#: an integrity violation surfacing three layers up.
_SLUG_ATTEMPTS: Final = 8


def _uuid(value: str, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise InvalidBallotDataError(f"Некорректный идентификатор: {what}.") from exc


def _optional_uuid(value: str | None, *, what: str) -> uuid.UUID | None:
    return None if value in (None, "") else _uuid(str(value), what=what)


def _reveal(value: str) -> RevealPolicy:
    try:
        return RevealPolicy(value)
    except ValueError as exc:
        raise InvalidBallotDataError("Неизвестный режим показа результатов.") from exc


class BallotService:
    """Every use case of this context, over its two repositories."""

    def __init__(
        self,
        *,
        ballots: BallotRepository,
        votes: VoteRepository,
        clock: Clock,
        uuids: UuidGenerator,
        slugs: SlugFactory,
        catalog: NomineeCatalog | None = None,
    ) -> None:
        self._ballots = ballots
        self._votes = votes
        self._clock = clock
        self._uuids = uuids
        self._slugs = slugs
        self._catalog = catalog

    # ------------------------------------------------------------------
    # The organizer's ballots
    # ------------------------------------------------------------------

    def list_ballots(self, organization_id: uuid.UUID, *, competition_id: uuid.UUID | None = None) -> list[BallotSummaryView]:
        """Every ballot this organization runs, newest first."""
        return [_summary(ballot) for ballot in self._ballots.list_for_organization(organization_id, competition_id=competition_id)]

    def create(self, command: CreateBallotCommand) -> BallotDetailView:
        """Start a ballot, standalone or attached to a festival."""
        now = self._clock.utcnow()
        ballot = Ballot.draft(
            ballot_id=self._uuids.new(),
            organization_id=_uuid(command.organization_id, what="организация"),
            title=BallotTitle(command.title),
            slug=self._mint_slug(),
            now=now,
            competition_id=_optional_uuid(command.competition_id, what="фестиваль"),
            description=(command.description or "").strip(),
            window=VotingWindow(opens_at=command.opens_at, closes_at=command.closes_at),
            vote_limit=VoteLimit(command.votes_per_voter),
            cooldown=Cooldown(command.cooldown_hours),
            reveal=_reveal(command.reveal),
        )
        self._ballots.save(ballot)
        return self._detail(ballot)

    def get(self, ballot_id: uuid.UUID) -> BallotDetailView:
        """One ballot, as the organizer edits it."""
        return self._detail(self._load(ballot_id))

    def update(self, command: UpdateBallotCommand) -> BallotDetailView:
        """Change the wording or the rules."""
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        ballot.update(
            now=self._clock.utcnow(),
            title=BallotTitle(command.title) if command.title is not None else None,
            description=command.description,
            window=VotingWindow(opens_at=command.opens_at, closes_at=command.closes_at) if command.window_given else None,
            vote_limit=VoteLimit(command.votes_per_voter) if command.votes_per_voter is not None else None,
            cooldown=Cooldown(command.cooldown_hours) if command.cooldown_hours is not None else None,
            reveal=_reveal(command.reveal) if command.reveal is not None else None,
        )
        self._ballots.save(ballot)
        return self._detail(ballot)

    def delete(self, ballot_id: uuid.UUID) -> None:
        """Retire a ballot. The votes stay where they are."""
        ballot = self._load(ballot_id)
        self._ballots.soft_delete(ballot, now=self._clock.utcnow())

    def open(self, ballot_id: uuid.UUID) -> BallotDetailView:
        """Start accepting votes."""
        ballot = self._load(ballot_id)
        ballot.open(now=self._clock.utcnow())
        self._ballots.save(ballot)
        return self._detail(ballot)

    def close(self, ballot_id: uuid.UUID) -> BallotDetailView:
        """Stop accepting votes, for good."""
        ballot = self._load(ballot_id)
        ballot.close(now=self._clock.utcnow())
        self._ballots.save(ballot)
        return self._detail(ballot)

    # ------------------------------------------------------------------
    # The list of nominees
    # ------------------------------------------------------------------

    def add_nominee(self, command: AddNomineeCommand) -> BallotDetailView:
        """Put one more nominee on the ballot."""
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        self._append(ballot, command.nominee, now=self._clock.utcnow())
        self._ballots.save(ballot)
        return self._detail(ballot)

    def edit_nominee(self, command: EditNomineeCommand) -> BallotDetailView:
        """Correct a nominee's card."""
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        nominee = ballot.nominee(_uuid(command.nominee_id, what="номинант"))
        nominee.edit(
            title=NomineeText(command.title) if command.title is not None else None,
            subtitle=NomineeText(command.subtitle) if command.subtitle is not None else None,
            city=NomineeText(command.city) if command.city is not None else None,
            photo=command.photo,
            number=command.number,
        )
        ballot.update(now=self._clock.utcnow())
        self._ballots.save(ballot)
        return self._detail(ballot)

    def remove_nominee(self, ballot_id: uuid.UUID, nominee_id: uuid.UUID) -> BallotDetailView:
        """Take a nominee off — erased if nobody voted, withdrawn if they did."""
        ballot = self._load(ballot_id)
        ballot.remove_nominee(nominee_id, now=self._clock.utcnow())
        self._ballots.save(ballot)
        return self._detail(ballot)

    def reorder_nominees(self, command: ReorderNomineesCommand) -> BallotDetailView:
        """Rearrange the list."""
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        ballot.reorder_nominees(
            [_uuid(value, what="номинант") for value in command.order],
            now=self._clock.utcnow(),
        )
        self._ballots.save(ballot)
        return self._detail(ballot)

    def import_nominees(self, command: ImportNomineesCommand) -> ImportPreviewView:
        """Add a batch from a spreadsheet, or preview what adding it would do.

        The preview and the real thing run the same code and differ only in whether
        the result is saved, so what the organizer agreed to is what happens.
        """
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        now = self._clock.utcnow()

        added: list[BallotNominee] = []
        errors = list(command.rejected)
        for offset, row in enumerate(command.rows, start=1):
            try:
                added.append(self._append(ballot, row, now=now))
            except InvalidBallotDataError as exc:
                errors.append((offset, str(exc)))

        if not command.dry_run and added:
            self._ballots.save(ballot)

        return ImportPreviewView(
            added=tuple(_nominee(nominee) for nominee in added),
            errors=tuple(sorted(errors)),
            dry_run=command.dry_run,
        )

    def seed_from_program(self, command: SeedFromProgramCommand) -> BallotDetailView:
        """Fill the list from a programme of the festival this ballot belongs to.

        The one place the festival half of the platform is touched, and it is a
        *copy*: what comes back is flat data that becomes the ballot's own nominees.
        Everything downstream is identical to a list typed in by hand — which is why
        a standalone ballot needs none of this.
        """
        ballot = self._load(_uuid(command.ballot_id, what="голосование"))
        if self._catalog is None:  # pragma: no cover - wiring fault, not a request fault
            raise InvalidBallotDataError("Импорт из программы недоступен.")
        if ballot.competition_id is None:
            raise InvalidBallotDataError("Это голосование не привязано к фестивалю — добавьте номинантов вручную или из файла.")

        now = self._clock.utcnow()
        acts = self._catalog.for_program(_uuid(command.program_id, what="программа"), organization_id=ballot.organization_id)
        # Acts already on the ballot are skipped rather than duplicated: seeding a
        # second time after the running order changed should top the list up.
        seeded = {nominee.program_item_id for nominee in ballot.nominees if nominee.program_item_id is not None}
        for act in acts:
            if act.program_item_id is not None and act.program_item_id in seeded:
                continue
            ballot.add_nominee(
                nominee_id=self._uuids.new(),
                title=NomineeText(act.title),
                subtitle=NomineeText(act.subtitle),
                city=NomineeText(act.city),
                number=act.number,
                submission_id=act.submission_id,
                program_item_id=act.program_item_id,
                now=now,
            )
        self._ballots.save(ballot)
        return self._detail(ballot)

    # ------------------------------------------------------------------
    # The public side
    # ------------------------------------------------------------------

    def public_view(self, slug: str, *, tokens: VoterTokens) -> PublicBallotView:
        """The voting page, as it looks to the reader these tokens identify.

        Who the reader is arrives already resolved: recognizing them is an HTTP
        concern (a cookie, an address) and belongs at the edge, so this layer never
        sees a request object and can be exercised with a pair of strings.
        """
        return self._public(self._load_public(slug), tokens=tokens)

    def cast_vote(self, command: CastVoteCommand, *, tokens: VoterTokens) -> VoteReceiptView:
        """Accept somebody's votes, or refuse the lot.

        All or nothing: a submission that spent two of three votes and then failed
        would leave the person looking at an error with no way to tell what counted.
        So every check runs before any vote is written.
        """
        ballot = self._load_public(slug=command.slug)
        now = self._clock.utcnow()
        bucket = ballot.cooldown.bucket(now)

        if not ballot.is_accepting_votes(now=now):
            raise VotingClosedError("Голосование сейчас не принимает голоса.")

        chosen = {_uuid(value, what="номинант") for value in command.nominee_ids}
        if not chosen:
            raise InvalidBallotDataError("Выберите хотя бы одного участника.")
        for nominee_id in chosen:
            # Raises if the nominee is not on this ballot at all.
            ballot.nominee(nominee_id)

        already = self._votes.chosen_by_voter(ballot_id=ballot.id, voter=tokens.voter, bucket=bucket)
        spent = len(already)
        fresh = chosen - already
        if not fresh:
            raise VoteLimitReachedError("Вы уже отдали свой голос за этих участников.")
        if spent + len(fresh) > ballot.vote_limit.value:
            left = max(0, ballot.vote_limit.value - spent)
            raise VoteLimitReachedError("Вы уже использовали все свои голоса." if left == 0 else f"У вас осталось голосов: {left}.")

        if self._votes.sent_by_network(ballot_id=ballot.id, network=tokens.network, bucket=bucket) + len(fresh) > NETWORK_VOTE_CEILING:
            raise TooManyVotesFromNetworkError("С этой сети уже пришло слишком много голосов. Попробуйте позже или с мобильного интернета.")

        accepted: list[uuid.UUID] = []
        for nominee_id in sorted(fresh, key=str):
            ballot.accept_vote_for(nominee_id, now=now)
            self._votes.cast(
                vote_id=self._uuids.new(),
                ballot_id=ballot.id,
                nominee_id=nominee_id,
                voter=tokens.voter,
                network=tokens.network,
                bucket=bucket,
                now=now,
            )
            accepted.append(nominee_id)

        # Re-read rather than render the aggregate we just mutated: the counts on it
        # are this process's arithmetic, and the database has everyone else's too.
        refreshed = self._ballots.get(ballot.id) or ballot
        return VoteReceiptView(
            ballot=self._public(refreshed, tokens=tokens),
            accepted=tuple(str(value) for value in accepted),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self, ballot_id: uuid.UUID) -> Ballot:
        ballot = self._ballots.get(ballot_id)
        if ballot is None:
            raise BallotNotFoundError("Голосование не найдено.")
        return ballot

    def _load_public(self, slug: str) -> Ballot:
        """Resolve a public link.

        A draft ballot is refused exactly like a slug that does not exist: a link
        handed out early must not confirm that something is being prepared.
        """
        ballot = self._ballots.find_by_slug(slug)
        if ballot is None or ballot.status is BallotStatus.DRAFT:
            raise BallotNotFoundError("Голосование не найдено.")
        return ballot

    def _mint_slug(self) -> PublicSlug:
        for _ in range(_SLUG_ATTEMPTS):
            candidate = self._slugs.new_slug()
            if not self._ballots.slug_exists(candidate):
                return PublicSlug(candidate)
        raise SlugUnavailableError("Не удалось создать ссылку на голосование. Попробуйте ещё раз.")

    def _append(self, ballot: Ballot, row: NomineeRow, *, now: datetime) -> BallotNominee:
        return ballot.add_nominee(
            nominee_id=self._uuids.new(),
            title=NomineeText(row.title),
            subtitle=NomineeText(row.subtitle),
            city=NomineeText(row.city),
            photo=row.photo,
            number=row.number,
            submission_id=_optional_uuid(row.submission_id, what="заявка"),
            program_item_id=_optional_uuid(row.program_item_id, what="строка программы"),
            now=now,
        )

    def _detail(self, ballot: Ballot) -> BallotDetailView:
        return BallotDetailView(
            id=str(ballot.id),
            title=ballot.title.value,
            description=ballot.description,
            slug=ballot.slug.value,
            status=ballot.status.value,
            competition_id=str(ballot.competition_id) if ballot.competition_id else None,
            standalone=ballot.standalone,
            opens_at=ballot.window.opens_at,
            closes_at=ballot.window.closes_at,
            votes_per_voter=ballot.vote_limit.value,
            cooldown_hours=ballot.cooldown.hours,
            reveal=ballot.reveal.value,
            nominees=tuple(_nominee(nominee) for nominee in ballot.nominees),
            total_votes=ballot.total_votes,
            voters=self._votes.voters(ballot.id),
            created_at=ballot.created_at,
            updated_at=ballot.updated_at,
        )

    def _public(self, ballot: Ballot, *, tokens: VoterTokens) -> PublicBallotView:
        now = self._clock.utcnow()
        bucket = ballot.cooldown.bucket(now)
        # A freshly minted token has cast nothing by definition, so a first-time
        # visitor costs no query here.
        chosen = set() if tokens.issued else self._votes.chosen_by_voter(ballot_id=ballot.id, voter=tokens.voter, bucket=bucket)
        reveal = ballot.may_reveal_totals(now=now)
        accepting = ballot.is_accepting_votes(now=now)

        return PublicBallotView(
            title=ballot.title.value,
            description=ballot.description,
            slug=ballot.slug.value,
            status=ballot.status.value,
            open=accepting,
            votes_per_voter=ballot.vote_limit.value,
            votes_left=max(0, ballot.vote_limit.value - len(chosen)),
            reveal_totals=reveal,
            nominees=tuple(
                PublicNomineeView(
                    id=str(nominee.id),
                    position=nominee.position,
                    title=nominee.title.value,
                    subtitle=nominee.subtitle.value,
                    city=nominee.city.value,
                    photo=nominee.photo,
                    number=nominee.number,
                    votes=nominee.votes if reveal else None,
                    chosen=nominee.id in chosen,
                )
                for nominee in ballot.votable
            ),
            total_votes=ballot.total_votes if reveal else None,
            closes_at=ballot.window.closes_at,
            closed_reason=None if accepting else _closed_reason(ballot, now=now),
        )


def _closed_reason(ballot: Ballot, *, now: datetime) -> str:
    """Why voting is not possible, in words for the person holding the phone."""
    if ballot.status is BallotStatus.CLOSED:
        return "Голосование завершено."
    if ballot.window.has_expired(now):
        return "Голосование завершено."
    if ballot.window.opens_at is not None and now < ballot.window.opens_at:
        return "Голосование ещё не началось."
    return "Голосование сейчас закрыто."


def _nominee(nominee: BallotNominee) -> NomineeView:
    return NomineeView(
        id=str(nominee.id),
        position=nominee.position,
        title=nominee.title.value,
        subtitle=nominee.subtitle.value,
        city=nominee.city.value,
        photo=nominee.photo,
        number=nominee.number,
        withdrawn=nominee.withdrawn,
        votes=nominee.votes,
        submission_id=str(nominee.submission_id) if nominee.submission_id else None,
        program_item_id=str(nominee.program_item_id) if nominee.program_item_id else None,
    )


def _summary(ballot: Ballot) -> BallotSummaryView:
    return BallotSummaryView(
        id=str(ballot.id),
        title=ballot.title.value,
        slug=ballot.slug.value,
        status=ballot.status.value,
        competition_id=str(ballot.competition_id) if ballot.competition_id else None,
        standalone=ballot.standalone,
        nominees=len(ballot.votable),
        total_votes=ballot.total_votes,
        opens_at=ballot.window.opens_at,
        closes_at=ballot.window.closes_at,
        created_at=ballot.created_at,
    )
