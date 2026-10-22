"""Use cases for the Judging bounded context.

Two services, split by who is using them and when.

:class:`JudgingConfigurationService` is the organizer between festivals: criteria, the
award scale, how marks are aggregated, who is on the panel. Everything here is slow,
deliberate and edited wholesale.

:class:`ScoringService` is the festival itself: the host moving through the running
order, judges sending sheets, the hall's board, the tally, and pushing the result into
the protocols the organizer publishes. Everything here happens once, on a day, on
venue wifi, and is written so a dropped connection costs one retry and nothing else.

A rule worth stating because it appears at the top of nearly every method below: **a
festival that is not on online judging cannot be scored.** It is checked in the service
rather than at a screen, because the thing that must not happen is a tablet left open
from last season writing marks into a festival whose organizer has since switched back
to protocols.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from apps.judging.application.commands import (
    AssignJuryMemberCommand,
    CloseScoringCommand,
    InviteJuryMemberCommand,
    OpenScoringCommand,
    SubmitScorecardCommand,
    UpdateAwardScaleCommand,
    UpdateBoardCommand,
    UpdateCriteriaCommand,
    UpdateJuryMemberCommand,
    UpdateScoringRulesCommand,
    UpdateTallyScopeCommand,
)
from apps.judging.application.dto import (
    AwardTierView,
    BoardEntryView,
    BoardJudgeView,
    BoardView,
    CriteriaSetView,
    CriterionView,
    JudgeScoreView,
    JudgingSetupView,
    JuryMemberView,
    JurySeatView,
    JuryTaskView,
    NominationView,
    PerformanceTallyView,
    RunningOrderEntryView,
    ScorecardView,
    ScoringStateView,
    TallyApplicationView,
    TallyGroupView,
    TallySheetView,
)
from apps.judging.application.interfaces import (
    AccountDirectory,
    Clock,
    CompetitionDirectory,
    DirectoryCompetition,
    DirectoryNomination,
    DirectoryPerformance,
    JudgingSetupRepository,
    JuryMemberRepository,
    JuryNotifier,
    PerformanceDirectory,
    PerformanceScoringRepository,
    ProtocolWriter,
    ScorecardRepository,
    SlugFactory,
    TokenFactory,
    UuidGenerator,
)
from apps.judging.domain.entities import JudgingSetup, JuryMember, PerformanceScoring, Scorecard
from apps.judging.domain.exceptions import (
    InvalidJudgingDataError,
    JuryMemberNotFoundError,
    NotAssignedToGenreError,
    OnlineJudgingDisabledError,
    ScoringNotFoundError,
    SetupNotFoundError,
)
from apps.judging.domain.services import PerformanceFacts, TallyKey, TallyService
from apps.judging.domain.value_objects import (
    AggregationMethod,
    AwardScale,
    AwardTier,
    BoardReveal,
    BoardSettings,
    BoardVisibility,
    CriteriaScope,
    CriteriaSet,
    Criterion,
    JuryMemberStatus,
    PerformanceScoringStatus,
    ScoringRules,
    parse_dimensions,
    parse_score,
)

__all__ = [
    "BOARD_PATH",
    "JURY_INVITE_PATH",
    "JudgingConfigurationService",
    "ScoringService",
]

#: The client-side routes the two links resolve to. Rendered into API responses so
#: neither the organizer's screen nor an invitation e-mail has to re-derive a URL shape.
BOARD_PATH = "/board/{slug}"
JURY_INVITE_PATH = "/jury/invite/{token}"

#: How many finished acts the hall's board keeps behind the current one. Enough to read
#: the last few results while the next act is announced, short enough that the screen
#: stays legible from the back of a room.
_BOARD_HISTORY = 5

#: A code minted from a label when the organizer did not supply one. Latin letters are
#: what the code alphabet allows, so a label written in Russian — which is nearly all of
#: them — falls through to the positional form below.
_CODE_FALLBACK = "TIER_{index}"


def _uuid(value: object, *, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidJudgingDataError(f"{what} должен быть идентификатором.") from exc


def _int(value: object, *, fallback: int) -> int:
    """Read a sort order off the wire, keeping the caller's position when it is junk."""
    try:
        return max(0, int(str(value)))
    except (TypeError, ValueError):
        return fallback


def _optional_uuid(value: object) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _mint_code(label: str, index: int) -> str:
    """Derive a stable code from a tier's label, or fall back to its position.

    Latin-alphabet labels ("Grand Prix") keep a readable code; Russian ones — the usual
    case — get ``TIER_3``. Readability is a nicety here: what the code has to be is
    stable and unique, and the label is what anybody ever reads.
    """
    candidate = "".join(char if char.isascii() and (char.isalnum() or char == "_") else "_" for char in label.strip().upper())
    candidate = candidate.strip("_")
    if candidate and candidate[0].isalpha():
        return candidate[:64]
    return _CODE_FALLBACK.format(index=index)


class _SetupMixin:
    """Loading the one configuration row, shared by both services."""

    _setups: JudgingSetupRepository
    _competitions: CompetitionDirectory
    _uuids: UuidGenerator
    _clock: Clock

    def _setup_for(self, competition_id: uuid.UUID) -> JudgingSetup:
        """This festival's configuration, defaulted if it has never been saved.

        A default that is *not* written to the database: reading the criteria screen of
        a festival nobody has configured should leave no trace, and every field has a
        defensible default, so an absent row and a fresh one mean the same thing.
        """
        stored = self._setups.get(competition_id)
        if stored is not None:
            return stored
        return JudgingSetup.create(setup_id=self._uuids.new(), competition_id=competition_id, now=self._clock.utcnow())

    def _require_online(self, competition_id: uuid.UUID) -> None:
        if not self._competitions.online_judging_enabled(competition_id):
            raise OnlineJudgingDisabledError("Для этого фестиваля не включено онлайн-судейство.")


class JudgingConfigurationService(_SetupMixin):
    """What an organizer sets up before a single mark is given."""

    def __init__(
        self,
        *,
        setups: JudgingSetupRepository,
        members: JuryMemberRepository,
        competitions: CompetitionDirectory,
        clock: Clock,
        uuids: UuidGenerator,
        slugs: SlugFactory,
        tokens: TokenFactory,
        notifier: JuryNotifier | None = None,
        accounts: AccountDirectory | None = None,
    ) -> None:
        self._setups = setups
        self._members = members
        self._competitions = competitions
        self._clock = clock
        self._uuids = uuids
        self._slugs = slugs
        self._tokens = tokens
        # Optional for the same reason the notifier is: a test that seats a panel need
        # not stand up Identity. Absent, an invitation is accepted by whoever follows
        # the link — which is the behaviour this shipped with and is why it is wired in
        # the composition root rather than left to each caller.
        self._accounts = accounts
        # Optional so a test that configures criteria need not stand up a mail gateway.
        # An invitation with no notifier is still recorded and its link still returned —
        # an organizer can copy it and send it themselves, which is what they do anyway
        # when a judge's mail bounces.
        self._notifier = notifier

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def setup(self, competition_id: str) -> JudgingSetupView:
        """The whole «Судейство» screen in one payload."""
        identifier = _uuid(competition_id, what="competitionId")
        setup = self._setup_for(identifier)
        nominations = self._competitions.nominations(identifier)
        names = self._target_names(nominations)
        members = self._members.by_competition(identifier)
        return JudgingSetupView(
            competition_id=str(identifier),
            online_judging=self._competitions.online_judging_enabled(identifier),
            award_scale=tuple(_tier_view(tier) for tier in setup.award_scale.tiers),
            criteria_sets=tuple(
                CriteriaSetView(
                    scope=item.scope.value,
                    target_id=str(item.target_id),
                    target_name=names.get(str(item.target_id)),
                    criteria=tuple(_criterion_view(criterion) for criterion in item.criteria),
                    max_total=item.max_total,
                )
                for item in sorted(setup.criteria_sets, key=lambda item: (item.scope.value, names.get(str(item.target_id)) or ""))
            ),
            nominations=tuple(
                NominationView(
                    category_id=str(item.category_id),
                    name=item.name,
                    disciplines=tuple((str(discipline_id), name) for discipline_id, name in item.disciplines),
                )
                for item in nominations
            ),
            aggregation=setup.scoring_rules.aggregation.value,
            drop_highest=setup.scoring_rules.drop_highest,
            drop_lowest=setup.scoring_rules.drop_lowest,
            tally_dimensions=tuple(dimension.value for dimension in setup.tally_scope.ordered()),
            board_enabled=setup.board.enabled,
            board_visibility=setup.board.visibility.value,
            board_reveal=setup.board.reveal.value,
            board_show_award=setup.board.show_award,
            board_show_running_order=setup.board.show_running_order,
            board_slug=setup.board_slug,
            board_path=BOARD_PATH.format(slug=setup.board_slug) if setup.board_slug else None,
            jury_count=sum(1 for member in members if member.status is not JuryMemberStatus.REVOKED),
            scale_is_banded=setup.award_scale.is_banded,
            updated_at=setup.updated_at,
        )

    def jury(self, competition_id: str) -> tuple[JuryMemberView, ...]:
        """The panel, in the order the organizer arranged it."""
        identifier = _uuid(competition_id, what="competitionId")
        names = {str(item.category_id): item.name for item in self._competitions.nominations(identifier)}
        return tuple(_member_view(member, names) for member in self._members.by_competition(identifier))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def update_criteria(self, command: UpdateCriteriaCommand) -> JudgingSetupView:
        """Replace one genre's or nomination's sheet.

        Criteria keep their ids across the save, which is the whole reason the payload
        carries them: an organizer who renames "Техника" mid-festival must not orphan
        every mark already given against it.
        """
        competition_id = _uuid(command.competition_id, what="competitionId")
        setup = self._setup_for(competition_id)
        try:
            scope = CriteriaScope(str(command.scope).upper())
        except ValueError as exc:
            raise InvalidJudgingDataError("Неизвестная область действия набора критериев.") from exc
        criteria = tuple(
            Criterion(
                id=_optional_uuid(entry.get("id")) or self._uuids.new(),
                name=str(entry.get("name", "")),
                max_score=parse_score(entry.get("maxScore", entry.get("max_score", 10)), what="Максимальный балл"),
                weight=parse_score(entry.get("weight", 1), what="Вес критерия"),
                sort_order=_int(entry.get("sortOrder", entry.get("sort_order", index)), fallback=index),
                description=entry.get("description"),  # type: ignore[arg-type]
            )
            for index, entry in enumerate(command.criteria)
        )
        setup.replace_criteria(
            CriteriaSet(scope=scope, target_id=_uuid(command.target_id, what="targetId"), criteria=criteria),
            now=self._clock.utcnow(),
        )
        self._setups.save(setup)
        return self.setup(str(competition_id))

    def update_award_scale(self, command: UpdateAwardScaleCommand) -> JudgingSetupView:
        """Replace the festival's award scale.

        Codes are preserved when supplied and minted when not. That matters on the
        second save of a scale somebody has already awarded from: a tier that came back
        with its code keeps naming the rows that won it, and one that came back without
        gets a new code and leaves those rows rendering from the built-in fallback.
        """
        competition_id = _uuid(command.competition_id, what="competitionId")
        setup = self._setup_for(competition_id)
        tiers: list[AwardTier] = []
        for index, entry in enumerate(command.tiers):
            label = str(entry.get("label", "")).strip()
            raw_code = str(entry.get("code", "")).strip()
            minimum = entry.get("minScore", entry.get("min_score"))
            maximum = entry.get("maxScore", entry.get("max_score"))
            tiers.append(
                AwardTier(
                    code=raw_code or _mint_code(label, index),
                    label=label,
                    min_score=parse_score(minimum, what="Нижний порог") if minimum not in (None, "") else None,
                    max_score=parse_score(maximum, what="Верхний порог") if maximum not in (None, "") else None,
                    sort_order=_int(entry.get("sortOrder", entry.get("sort_order", index)), fallback=index),
                )
            )
        if not tiers:
            raise InvalidJudgingDataError("Шкала наград не может быть пустой.")
        setup.replace_award_scale(AwardScale(tiers=tuple(tiers)), now=self._clock.utcnow())
        self._setups.save(setup)
        return self.setup(str(competition_id))

    def update_scoring_rules(self, command: UpdateScoringRulesCommand) -> JudgingSetupView:
        competition_id = _uuid(command.competition_id, what="competitionId")
        setup = self._setup_for(competition_id)
        try:
            aggregation = AggregationMethod(str(command.aggregation).upper())
        except ValueError as exc:
            raise InvalidJudgingDataError("Выберите, как считается итоговый балл.") from exc
        setup.change_scoring_rules(
            ScoringRules(aggregation=aggregation, drop_highest=command.drop_highest, drop_lowest=command.drop_lowest),
            now=self._clock.utcnow(),
        )
        self._setups.save(setup)
        return self.setup(str(competition_id))

    def update_tally_scope(self, command: UpdateTallyScopeCommand) -> JudgingSetupView:
        competition_id = _uuid(command.competition_id, what="competitionId")
        setup = self._setup_for(competition_id)
        setup.change_tally_scope(parse_dimensions(command.dimensions), now=self._clock.utcnow())
        self._setups.save(setup)
        return self.setup(str(competition_id))

    def update_board(self, command: UpdateBoardCommand) -> JudgingSetupView:
        """Change the hall's screen, minting its permanent link the first time it is on."""
        competition_id = _uuid(command.competition_id, what="competitionId")
        setup = self._setup_for(competition_id)
        try:
            visibility = BoardVisibility(str(command.visibility).upper())
            reveal = BoardReveal(str(command.reveal).upper())
        except ValueError as exc:
            raise InvalidJudgingDataError("Неизвестная настройка табло.") from exc
        setup.change_board(
            BoardSettings(
                enabled=command.enabled,
                visibility=visibility,
                reveal=reveal,
                show_award=command.show_award,
                show_running_order=command.show_running_order,
            ),
            now=self._clock.utcnow(),
            slug=self._slugs.new_slug(),
        )
        self._setups.save(setup)
        return self.setup(str(competition_id))

    # ------------------------------------------------------------------
    # The panel
    # ------------------------------------------------------------------

    def invite(self, command: InviteJuryMemberCommand) -> JuryMemberView:
        """Seat somebody on the panel and write to them.

        One seat per address per festival. The database enforces it too, but an
        organizer who adds the same judge twice deserves a sentence rather than a 500 —
        and it is a normal mistake with a panel typed in from a list.
        """
        competition_id = _uuid(command.competition_id, what="competitionId")
        now = self._clock.utcnow()
        existing = self._members.by_competition(competition_id)
        wanted = command.email.strip().lower()
        if any(member.email == wanted for member in existing):
            raise InvalidJudgingDataError("Этот адрес уже есть в составе жюри фестиваля.")
        token = self._tokens.new_token()
        member = JuryMember.create(
            member_id=self._uuids.new(),
            competition_id=competition_id,
            full_name=command.full_name,
            email=command.email,
            now=now,
            title=command.title,
            is_chair=command.is_chair,
            category_ids=[_uuid(item, what="categoryId") for item in command.category_ids],
            sort_order=len(existing),
            invitation_token=token,
        )
        self._members.save(member)
        self._send_invitation(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(competition_id)}
        return _member_view(member, names)

    def update_member(self, command: UpdateJuryMemberCommand) -> JuryMemberView:
        member = self._require_member(command.member_id)
        now = self._clock.utcnow()
        member.rename(full_name=command.full_name, title=command.title, now=now)
        member.make_chair(is_chair=command.is_chair, now=now)
        wanted = command.email.strip().lower()
        if wanted != member.email:
            taken = self._members.by_competition(member.competition_id)
            if any(other.id != member.id and other.email == wanted for other in taken):
                raise InvalidJudgingDataError("Этот адрес уже есть в составе жюри фестиваля.")
            member.change_email(command.email, now=now, invitation_token=self._tokens.new_token())
        self._members.save(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        return _member_view(member, names)

    def assign(self, command: AssignJuryMemberCommand) -> JuryMemberView:
        """Replace the genres a member judges."""
        member = self._require_member(command.member_id)
        member.assign_to([_uuid(item, what="categoryId") for item in command.category_ids], now=self._clock.utcnow())
        self._members.save(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        return _member_view(member, names)

    def reinvite(self, member_id: str) -> JuryMemberView:
        """Issue a fresh link, invalidating the one already sent."""
        member = self._require_member(member_id)
        member.reinvite(self._tokens.new_token(), now=self._clock.utcnow())
        self._members.save(member)
        self._send_invitation(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        return _member_view(member, names)

    def revoke(self, member_id: str) -> JuryMemberView:
        """Take the seat away, leaving every mark it gave in place."""
        member = self._require_member(member_id)
        member.revoke(now=self._clock.utcnow())
        self._members.save(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        return _member_view(member, names)

    def remove(self, member_id: str) -> None:
        """Remove the seat from the panel entirely.

        Soft-deleted, and the marks stay: a member added to the wrong festival is a
        normal mistake, and a member removed after a day of judging must not take their
        sheets out of an act's average on their way out.
        """
        member = self._require_member(member_id)
        self._members.delete(member.id)

    def accept_invitation(self, *, token: str, user_id: str) -> JuryMemberView:
        """Attach the account that followed an invitation link.

        The address is checked when the caller supplies one. An invitation is a seat on
        a named person's behalf, and the letter it arrived in is forwardable — without
        this, the first colleague somebody forwards it to becomes the judge, and the
        organizer sees the right name in the panel with the wrong person behind it.
        """
        member = self._members.by_invitation_token(token)
        if member is None:
            raise JuryMemberNotFoundError("Приглашение не найдено или уже использовано.")
        identifier = _uuid(user_id, what="userId")
        email = None if self._accounts is None else self._accounts.email_for(identifier)
        if email is not None and email != member.email:
            raise InvalidJudgingDataError(
                f"Приглашение отправлено на адрес {member.email}. Войдите под этим адресом или попросите организатора пригласить вас заново."
            )
        existing = self._members.by_user(competition_id=member.competition_id, user_id=identifier)
        if existing is not None and existing.id != member.id:
            raise InvalidJudgingDataError("Этот аккаунт уже состоит в жюри фестиваля.")
        member.accept(user_id=identifier, now=self._clock.utcnow())
        self._members.save(member)
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        return _member_view(member, names)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_member(self, member_id: str) -> JuryMember:
        member = self._members.get(_uuid(member_id, what="memberId"))
        if member is None:
            raise JuryMemberNotFoundError("Член жюри не найден.")
        return member

    def _send_invitation(self, member: JuryMember) -> None:
        if self._notifier is None or member.invitation_token is None:
            return
        self._notifier.notify_jury_invited(
            email=member.email,
            full_name=member.full_name,
            competition_title=self._competitions.competition_title(member.competition_id),
            invitation_url=JURY_INVITE_PATH.format(token=member.invitation_token),
        )

    @staticmethod
    def _target_names(nominations: Sequence[DirectoryNomination]) -> dict[str, str]:
        """Genre and nomination ids → their names, so a sheet lists without a join."""
        names: dict[str, str] = {}
        for item in nominations:
            names[str(item.category_id)] = item.name
            for discipline_id, discipline_name in item.disciplines:
                names[str(discipline_id)] = discipline_name
        return names


class ScoringService(_SetupMixin):
    """The festival itself: the running order, the sheets, the board and the tally."""

    def __init__(
        self,
        *,
        setups: JudgingSetupRepository,
        members: JuryMemberRepository,
        scorings: PerformanceScoringRepository,
        scorecards: ScorecardRepository,
        competitions: CompetitionDirectory,
        performances: PerformanceDirectory,
        clock: Clock,
        uuids: UuidGenerator,
        protocols: ProtocolWriter | None = None,
    ) -> None:
        self._setups = setups
        self._members = members
        self._scorings = scorings
        self._scorecards = scorecards
        self._competitions = competitions
        self._performances = performances
        self._clock = clock
        self._uuids = uuids
        # Optional: everything except "перенести в протоколы" works without it.
        self._protocols = protocols

    # ------------------------------------------------------------------
    # The host drives the day
    # ------------------------------------------------------------------

    def open_scoring(self, command: OpenScoringCommand) -> ScoringStateView:
        """Put an act on stage. The panel's tablets follow."""
        competition_id = _uuid(command.competition_id, what="competitionId")
        self._require_online(competition_id)
        now = self._clock.utcnow()
        if command.close_previous:
            current = self._scorings.current(competition_id)
            if current is not None and current.submission_id != _uuid(command.submission_id, what="submissionId"):
                current.close(now=now)
                self._scorings.save(current)
        scoring = self._scoring_for(competition_id, _uuid(command.submission_id, what="submissionId"), now=now)
        scoring.open(now=now)
        self._scorings.save(scoring)
        return _scoring_view(scoring)

    def close_scoring(self, command: CloseScoringCommand) -> ScoringStateView:
        """Freeze an act's marks. Under ``AFTER_CLOSE`` the hall sees them now."""
        competition_id = _uuid(command.competition_id, what="competitionId")
        self._require_online(competition_id)
        now = self._clock.utcnow()
        scoring = self._scorings.get(competition_id=competition_id, submission_id=_uuid(command.submission_id, what="submissionId"))
        if scoring is None:
            raise ScoringNotFoundError("Это выступление не открывалось для оценки.")
        scoring.close(now=now)
        self._scorings.save(scoring)
        return _scoring_view(scoring)

    def states(self, competition_id: str) -> tuple[ScoringStateView, ...]:
        identifier = _uuid(competition_id, what="competitionId")
        return tuple(_scoring_view(item) for item in self._scorings.by_competition(identifier))

    def running_order(self, competition_id: str) -> tuple[RunningOrderEntryView, ...]:
        """The programme, in programme order, with each act's state on it.

        The host's list, and separate from :meth:`tally` on purpose. A tally is sorted
        by score so results read top-down; a host announces numbers in the order the
        hall will hear them, and a screen that reorders itself every time an act is
        marked is one the host stops trusting by the third number.
        """
        identifier = _uuid(competition_id, what="competitionId")
        self._require_online(identifier)
        setup = self._setup_for(identifier)
        tally = TallyService(setup)
        performances = self._performances.performances(identifier)
        cards = self._scorecards.by_submissions(competition_id=identifier, submission_ids=[item.submission_id for item in performances])
        members = self._members.by_competition(identifier)
        states = {item.submission_id: item.status.value for item in self._scorings.by_competition(identifier)}

        entries: list[RunningOrderEntryView] = []
        for performance in performances:
            result = tally.tally(
                facts=_facts(performance),
                scorecards=cards.get(performance.submission_id, ()),
                expected_judges=self._expected_judges(members, performance.category_id),
            )
            entries.append(
                RunningOrderEntryView(
                    submission_id=str(performance.submission_id),
                    number=performance.number,
                    title=performance.title,
                    category_name=performance.category_name,
                    discipline_name=performance.discipline_name,
                    age_category_name=performance.age_category_name,
                    organization=performance.organization,
                    status=states.get(performance.submission_id, PerformanceScoringStatus.PENDING.value),
                    submitted_count=result.submitted_count,
                    expected_judges=result.expected_judges,
                    score=result.score,
                    award_label=result.award_label,
                )
            )
        return tuple(entries)

    # ------------------------------------------------------------------
    # The judge's tablet
    # ------------------------------------------------------------------

    def seats_for_judge(self, user_id: str) -> tuple[JurySeatView, ...]:
        """Every festival this account judges — the judge's way back into the platform.

        Only accepted seats, and only festivals still on online judging: a revoked
        member and a festival switched back to protocols both mean "there is nothing
        here for you", and listing either would hand somebody a screen that refuses
        every button on it.

        Soonest first, with undated festivals last. A judge opens this on the morning
        of the thing they are judging.
        """
        identifier = _uuid(user_id, what="userId")
        seats = self._members.competitions_for_user(identifier)
        if not seats:
            return ()
        festivals = self._competitions.competitions([member.competition_id for member in seats])
        views: list[JurySeatView] = []
        for member in seats:
            festival = festivals.get(member.competition_id)
            if festival is None or not festival.online_judging:
                continue
            views.append(self._seat_view(member, festival))
        return tuple(sorted(views, key=_seat_sort))

    def tasks_for_judge(self, *, competition_id: str, user_id: str) -> tuple[JuryTaskView, ...]:
        """Every act this judge is seated for, with their own marks filled in.

        The whole list rather than only the act on stage: a judge who missed a number
        has to be able to go back to it, which is what the organizer asked for. What
        they cannot do is *write* to one the host has closed.
        """
        identifier = _uuid(competition_id, what="competitionId")
        self._require_online(identifier)
        member = self._require_seat(identifier, user_id)
        setup = self._setup_for(identifier)
        performances = [item for item in self._performances.performances(identifier) if member.judges(item.category_id)]
        states = {item.submission_id: item for item in self._scorings.by_competition(identifier)}
        cards = {card.submission_id: card for card in self._scorecards.by_member(competition_id=identifier, jury_member_id=member.id)}
        tasks: list[JuryTaskView] = []
        for performance in performances:
            criteria = setup.criteria_for(category_id=performance.category_id, discipline_id=performance.discipline_id)
            state = states.get(performance.submission_id)
            card = cards.get(performance.submission_id)
            status = state.status.value if state is not None else PerformanceScoringStatus.PENDING.value
            tasks.append(
                JuryTaskView(
                    submission_id=str(performance.submission_id),
                    number=performance.number,
                    title=performance.title,
                    category_id=str(performance.category_id),
                    category_name=performance.category_name,
                    discipline_name=performance.discipline_name,
                    age_category_name=performance.age_category_name,
                    participation_format_name=performance.participation_format_name,
                    organization=performance.organization,
                    status=status,
                    criteria=tuple(_criterion_view(criterion) for criterion in criteria),
                    my_scores=tuple(JudgeScoreView(criterion_id=str(item.criterion_id), score=item.score) for item in card.scores) if card else (),
                    my_comment=card.comment if card else None,
                    my_total=card.total(criteria) if card and card.is_submitted else None,
                    submitted_at=card.submitted_at if card else None,
                    can_score=bool(criteria) and member.can_score and state is not None and state.is_open,
                    max_total=setup.max_total_for(category_id=performance.category_id, discipline_id=performance.discipline_id),
                )
            )
        return tuple(tasks)

    def submit_scorecard(self, command: SubmitScorecardCommand) -> JuryTaskView:
        """One judge sending their sheet, or correcting the one they sent."""
        competition_id = _uuid(command.competition_id, what="competitionId")
        self._require_online(competition_id)
        submission_id = _uuid(command.submission_id, what="submissionId")
        member = self._require_seat(competition_id, command.user_id)
        if not member.can_score:
            raise NotAssignedToGenreError("Приглашение в жюри ещё не принято.")

        performance = self._performances.performances_by_id([submission_id]).get(submission_id)
        if performance is None:
            raise ScoringNotFoundError("Выступление не найдено.")
        if not member.judges(performance.category_id):
            raise NotAssignedToGenreError("Вы не судите этот жанр.")

        scoring = self._scorings.get(competition_id=competition_id, submission_id=submission_id)
        if scoring is None:
            raise ScoringNotFoundError("Это выступление ещё не открыли для оценки.")
        # The rule that would be a single-aggregate invariant if the panel could afford
        # one — see the note at the top of `domain.entities`.
        scoring.require_open()

        setup = self._setup_for(competition_id)
        criteria = setup.criteria_for(category_id=performance.category_id, discipline_id=performance.discipline_id)
        now = self._clock.utcnow()
        card = self._scorecards.get(competition_id=competition_id, submission_id=submission_id, jury_member_id=member.id) or Scorecard.create(
            scorecard_id=self._uuids.new(),
            competition_id=competition_id,
            submission_id=submission_id,
            jury_member_id=member.id,
            now=now,
        )
        card.submit(
            scores={_uuid(key, what="criterionId"): parse_score(value, what="Балл") for key, value in command.scores.items()},
            criteria=criteria,
            comment=command.comment,
            now=now,
        )
        self._scorecards.save(card)
        return JuryTaskView(
            submission_id=str(submission_id),
            number=performance.number,
            title=performance.title,
            category_id=str(performance.category_id),
            category_name=performance.category_name,
            discipline_name=performance.discipline_name,
            age_category_name=performance.age_category_name,
            participation_format_name=performance.participation_format_name,
            organization=performance.organization,
            status=scoring.status.value,
            criteria=tuple(_criterion_view(criterion) for criterion in criteria),
            my_scores=tuple(JudgeScoreView(criterion_id=str(item.criterion_id), score=item.score) for item in card.scores),
            my_comment=card.comment,
            my_total=card.total(criteria),
            submitted_at=card.submitted_at,
            can_score=scoring.is_open,
            max_total=setup.max_total_for(category_id=performance.category_id, discipline_id=performance.discipline_id),
        )

    # ------------------------------------------------------------------
    # The organizer's tally
    # ------------------------------------------------------------------

    def tally(self, competition_id: str) -> TallySheetView:
        """Every act reckoned, grouped the way the festival announces."""
        identifier = _uuid(competition_id, what="competitionId")
        setup = self._setup_for(identifier)
        tally = TallyService(setup)
        performances = self._performances.performances(identifier)
        facts = [_facts(item) for item in performances]
        by_id = {item.submission_id: item for item in performances}
        cards = self._scorecards.by_submissions(competition_id=identifier, submission_ids=[item.submission_id for item in performances])
        members = {member.id: member for member in self._members.by_competition(identifier)}
        panel = tuple(members.values())
        expected = {item.submission_id: self._expected_judges(panel, item.category_id) for item in performances}
        states = {item.submission_id: item.status.value for item in self._scorings.by_competition(identifier)}
        names = self._axis_names(performances)

        groups: list[TallyGroupView] = []
        unawarded = 0
        for group in tally.group(facts=facts, scorecards_by_submission=cards, expected_by_submission=expected):
            views: list[PerformanceTallyView] = []
            for item in group.tallies:
                performance = by_id[item.submission_id]
                if item.score is not None and item.award_code is None:
                    unawarded += 1
                views.append(
                    PerformanceTallyView(
                        submission_id=str(item.submission_id),
                        number=performance.number,
                        title=performance.title,
                        organization=performance.organization,
                        score=item.score,
                        max_score=item.max_score,
                        award_code=item.award_code,
                        award_label=item.award_label,
                        submitted_count=item.submitted_count,
                        expected_judges=item.expected_judges,
                        status=states.get(item.submission_id, PerformanceScoringStatus.PENDING.value),
                        scorecards=tuple(
                            ScorecardView(
                                jury_member_id=str(card.jury_member_id),
                                jury_member_name=(members[card.jury_member_id].full_name if card.jury_member_id in members else "Член жюри"),
                                scores=tuple(JudgeScoreView(criterion_id=str(score.criterion_id), score=score.score) for score in card.scores),
                                total=card.total(tally.criteria_for(_facts(performance))),
                                comment=card.comment,
                                submitted_at=card.submitted_at,
                                submitted=card.is_submitted,
                            )
                            for card in cards.get(item.submission_id, ())
                        ),
                    )
                )
            groups.append(
                TallyGroupView(
                    key=_group_key(group.key),
                    heading=_group_heading(group.key, names),
                    category_id=str(group.key.category_id) if group.key.category_id else None,
                    tallies=tuple(views),
                )
            )
        return TallySheetView(
            competition_id=str(identifier),
            groups=tuple(groups),
            aggregation=setup.scoring_rules.aggregation.value,
            scale_is_banded=setup.award_scale.is_banded,
            unawarded_count=unawarded,
        )

    def apply_to_protocols(self, competition_id: str, *, create_missing: bool = False) -> TallyApplicationView:
        """Write the computed awards into the protocols the organizer publishes.

        The push is deliberately one-way and repeatable: the protocol stays editable
        afterwards, so an organizer who fixes a row by hand keeps that fix until
        somebody presses this again, and pressing it again is how they discard it.
        Nothing is published here — publication stays the deliberate act it has always
        been.

        What it reports back matters as much as what it writes. A genre with no
        protocol open is named rather than counted as "nothing to change": those are
        different situations, and only one of them is finished. ``create_missing``
        opens those protocols from the programme first, which is what an online-judged
        festival means by "протоколы заполняются сами".
        """
        if self._protocols is None:
            raise SetupNotFoundError("Перенос в протоколы недоступен.")
        identifier = _uuid(competition_id, what="competitionId")
        self._require_online(identifier)
        setup = self._setup_for(identifier)
        tally = TallyService(setup)
        performances = self._performances.performances(identifier)
        cards = self._scorecards.by_submissions(competition_id=identifier, submission_ids=[item.submission_id for item in performances])
        members = self._members.by_competition(identifier)
        now = self._clock.utcnow()

        # Grouped by genre rather than by the tally's own grouping: a protocol is a
        # genre's document whatever axes the festival announces by, so a festival that
        # separates by age still writes into one protocol per genre.
        by_category: dict[uuid.UUID, list[tuple[uuid.UUID, str | None]]] = {}
        for performance in performances:
            result = tally.tally(
                facts=_facts(performance),
                scorecards=cards.get(performance.submission_id, ()),
                expected_judges=self._expected_judges(members, performance.category_id),
            )
            if result.score is None:
                # Nobody marked this act. Leaving the protocol's row alone is the point:
                # an organizer may have typed that result in by hand.
                continue
            by_category.setdefault(performance.category_id, []).append((performance.submission_id, result.award_code))

        names = {str(item.category_id): item.name for item in self._competitions.nominations(identifier)}
        changed = 0
        created = 0
        missing: list[str] = []
        for category_id, awards in by_category.items():
            applied = self._protocols.apply_awards(
                competition_id=identifier,
                nomination_id=category_id,
                awards=awards,
                now=now,
                create_missing=create_missing,
            )
            changed += applied.rows_changed
            if applied.protocol_created:
                created += 1
            if not applied.protocol_existed:
                missing.append(names.get(str(category_id), "Без жанра"))
        return TallyApplicationView(rows_changed=changed, protocols_created=created, missing_protocols=tuple(sorted(missing)))

    # ------------------------------------------------------------------
    # The hall's board
    # ------------------------------------------------------------------

    def board(self, slug: str) -> BoardView | None:
        """The public screen, assembled to exactly what the organizer allowed.

        The filtering happens here and not in a serializer. A board configured to show
        totals only must not be one query parameter away from naming every judge, and
        the way to guarantee that is for the per-judge marks never to leave this method.
        """
        setup = self._setups.by_board_slug(slug)
        if setup is None:
            return None
        competition_id = setup.competition_id
        tally = TallyService(setup)
        performances = {item.submission_id: item for item in self._performances.performances(competition_id)}
        states = sorted(
            (item for item in self._scorings.by_competition(competition_id) if item.status is not PerformanceScoringStatus.PENDING),
            key=lambda item: item.opened_at or item.updated_at,
            reverse=True,
        )
        members = self._members.by_competition(competition_id)
        names = {member.id: member.full_name for member in members}
        wanted = [item.submission_id for item in states[: _BOARD_HISTORY + 1]]
        cards = self._scorecards.by_submissions(competition_id=competition_id, submission_ids=wanted)

        # Paired with their state as they are built. An act whose entry is skipped —
        # withdrawn from Applications since the host opened it — would otherwise shift
        # the list against ``states`` and make the board point at the wrong number.
        entries: list[tuple[PerformanceScoring, BoardEntryView]] = []
        for state in states[: _BOARD_HISTORY + 1]:
            performance = performances.get(state.submission_id)
            if performance is None:
                continue
            result = tally.tally(
                facts=_facts(performance),
                scorecards=cards.get(state.submission_id, ()),
                expected_judges=self._expected_judges(members, performance.category_id),
            )
            revealed = setup.board.reveal is BoardReveal.IMMEDIATE or state.is_closed
            entry = BoardEntryView(
                number=performance.number,
                title=performance.title,
                organization=performance.organization,
                category_name=performance.category_name,
                age_category_name=performance.age_category_name,
                status=state.status.value,
                score=result.score if revealed else None,
                max_score=result.max_score,
                award_label=result.award_label if revealed and setup.board.show_award else None,
                submitted_count=result.submitted_count,
                expected_judges=result.expected_judges,
                judges=(
                    tuple(
                        BoardJudgeView(name=names.get(item.jury_member_id, "Член жюри"), total=item.total if item.submitted else None)
                        for item in result.judge_totals
                    )
                    if revealed and setup.board.visibility is BoardVisibility.PER_JUDGE
                    else ()
                ),
            )
            entries.append((state, entry))
        current = next((entry for state, entry in entries if state.is_open), None)
        return BoardView(
            competition_title=self._competitions.competition_title(competition_id),
            visibility=setup.board.visibility.value,
            reveal=setup.board.reveal.value,
            show_award=setup.board.show_award,
            current=current,
            recent=tuple(entry for _, entry in entries if entry is not current)[:_BOARD_HISTORY] if setup.board.show_running_order else (),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _seat_view(self, member: JuryMember, festival: DirectoryCompetition) -> JurySeatView:
        """One row of the judge's own festival list, with how much is left on it."""
        performances = [item for item in self._performances.performances(member.competition_id) if member.judges(item.category_id)]
        own_cards = self._scorecards.by_member(competition_id=member.competition_id, jury_member_id=member.id)
        scored = {card.submission_id for card in own_cards if card.is_submitted}
        states = {item.submission_id: item for item in self._scorings.by_competition(member.competition_id)}
        names = {str(item.category_id): item.name for item in self._competitions.nominations(member.competition_id)}
        pending = 0
        has_open = False
        for performance in performances:
            state = states.get(performance.submission_id)
            if state is not None and state.is_open:
                has_open = True
            if performance.submission_id not in scored:
                pending += 1
        return JurySeatView(
            competition_id=str(member.competition_id),
            title=festival.title,
            online_judging=festival.online_judging,
            is_chair=member.is_chair,
            category_names=tuple(names[str(item)] for item in member.category_ids if str(item) in names),
            starts_on=festival.starts_on,
            ends_on=festival.ends_on,
            venue=festival.venue,
            pending_count=pending,
            has_open_act=has_open,
        )

    def _require_seat(self, competition_id: uuid.UUID, user_id: str) -> JuryMember:
        member = self._members.by_user(competition_id=competition_id, user_id=_uuid(user_id, what="userId"))
        if member is None or member.status is JuryMemberStatus.REVOKED:
            raise JuryMemberNotFoundError("Вы не входите в жюри этого фестиваля.")
        return member

    def _scoring_for(self, competition_id: uuid.UUID, submission_id: uuid.UUID, *, now: datetime) -> PerformanceScoring:
        return self._scorings.get(competition_id=competition_id, submission_id=submission_id) or PerformanceScoring.create(
            scoring_id=self._uuids.new(),
            competition_id=competition_id,
            submission_id=submission_id,
            now=now,
        )

    @staticmethod
    def _expected_judges(members: Sequence[JuryMember], category_id: uuid.UUID) -> int:
        """How many sheets this act should end up with.

        Counts the seats that can actually write — accepted, with an account, seated for
        the genre. A judge who never accepted their invitation must not leave every act
        of their genre reading "3 из 4" for the whole festival.
        """
        return sum(1 for member in members if member.can_score and member.judges(category_id))

    @staticmethod
    def _axis_names(performances: Sequence[DirectoryPerformance]) -> dict[str, str]:
        names: dict[str, str] = {}
        for item in performances:
            if item.category_name:
                names[str(item.category_id)] = item.category_name
            if item.discipline_id and item.discipline_name:
                names[str(item.discipline_id)] = item.discipline_name
            if item.age_category_id and item.age_category_name:
                names[str(item.age_category_id)] = item.age_category_name
            if item.participation_format_id and item.participation_format_name:
                names[str(item.participation_format_id)] = item.participation_format_name
        return names


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------


def _seat_sort(seat: JurySeatView) -> tuple[int, str, str]:
    """Soonest festival first; the undated ones last, alphabetically."""
    return (1, "", seat.title.lower()) if seat.starts_on is None else (0, seat.starts_on.isoformat(), seat.title.lower())


def _criterion_view(criterion: Criterion) -> CriterionView:
    return CriterionView(
        id=str(criterion.id),
        name=criterion.name,
        max_score=criterion.max_score,
        weight=criterion.weight,
        sort_order=criterion.sort_order,
        description=criterion.description,
    )


def _tier_view(tier: AwardTier) -> AwardTierView:
    return AwardTierView(
        code=tier.code,
        label=tier.label,
        min_score=tier.min_score,
        max_score=tier.max_score,
        sort_order=tier.sort_order,
    )


def _member_view(member: JuryMember, names: Mapping[str, str]) -> JuryMemberView:
    return JuryMemberView(
        id=str(member.id),
        full_name=member.full_name,
        email=member.email,
        title=member.title,
        status=member.status.value,
        is_chair=member.is_chair,
        category_ids=tuple(str(item) for item in member.category_ids),
        category_names=tuple(name for name in (names.get(str(item)) for item in member.category_ids) if name),
        sort_order=member.sort_order,
        has_account=member.user_id is not None,
        invited_at=member.invited_at,
        accepted_at=member.accepted_at,
        invitation_path=JURY_INVITE_PATH.format(token=member.invitation_token) if member.invitation_token else None,
    )


def _scoring_view(scoring: PerformanceScoring) -> ScoringStateView:
    return ScoringStateView(
        submission_id=str(scoring.submission_id),
        status=scoring.status.value,
        opened_at=scoring.opened_at,
        closed_at=scoring.closed_at,
    )


def _facts(performance: DirectoryPerformance) -> PerformanceFacts:
    return PerformanceFacts(
        submission_id=performance.submission_id,
        category_id=performance.category_id,
        discipline_id=performance.discipline_id,
        age_category_id=performance.age_category_id,
        participation_format_id=performance.participation_format_id,
    )


def _key_parts(key: TallyKey) -> tuple[str, str, str, str]:
    return (
        str(key.category_id or ""),
        str(key.discipline_id or ""),
        str(key.age_category_id or ""),
        str(key.participation_format_id or ""),
    )


def _group_key(key: TallyKey) -> str:
    """A stable client-side identity for one sheet of results."""
    return "|".join(_key_parts(key))


def _group_heading(key: TallyKey, names: Mapping[str, str]) -> str:
    """How one sheet of results is titled: every axis the festival separates by, joined."""
    joined = " · ".join(part for part in (names.get(item) for item in _key_parts(key) if item) if part)
    return joined or "Итоги"
