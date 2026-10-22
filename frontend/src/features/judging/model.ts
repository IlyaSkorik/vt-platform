/**
 * The Judging context as the client sees it.
 *
 * Hand-written rather than generated, like the protocols feature next door: the
 * endpoints answer with the platform's `{data, meta}` envelope and camelCase bodies,
 * and a small typed surface reads better here than a generated client whose names are
 * derived from operation ids.
 *
 * **Every score is a string.** It is a decimal all the way down the backend, because a
 * jury's arithmetic is copied onto a diploma and `9.1` through a double is not `9.1`
 * any more. Parsing one to a number is fine for drawing a bar; comparing or summing
 * them in the browser is not, and nothing here does.
 */

export type JudgingScope = "CATEGORY" | "DISCIPLINE";
export type AggregationMethod = "AVERAGE" | "SUM";
export type TallyDimension = "CATEGORY" | "DISCIPLINE" | "AGE_CATEGORY" | "PARTICIPATION_FORMAT";
export type BoardVisibility = "PER_JUDGE" | "TOTAL_ONLY";
export type BoardReveal = "IMMEDIATE" | "AFTER_CLOSE";
export type JuryStatus = "INVITED" | "ACTIVE" | "REVOKED";
export type ScoringStatus = "PENDING" | "OPEN" | "CLOSED";

export interface Criterion {
  id: string;
  name: string;
  /** The most a judge may give on this line. */
  maxScore: string;
  /** How much that mark counts toward the act's total. */
  weight: string;
  sortOrder: number;
  description: string | null;
}

export interface CriteriaSet {
  scope: JudgingScope;
  targetId: string;
  targetName: string | null;
  criteria: Criterion[];
  /** The most one judge can give under this sheet — what award bands are sized against. */
  maxTotal: string;
}

export interface AwardTier {
  code: string;
  label: string;
  /** Inclusive, and either end may be absent: the top tier usually has no ceiling. */
  minScore: string | null;
  maxScore: string | null;
  sortOrder: number;
}

export interface Nomination {
  categoryId: string;
  name: string;
  disciplines: { id: string; name: string }[];
}

export interface JudgingSetup {
  competitionId: string;
  onlineJudging: boolean;
  awardScale: AwardTier[];
  criteriaSets: CriteriaSet[];
  nominations: Nomination[];
  aggregation: AggregationMethod;
  dropHighest: boolean;
  dropLowest: boolean;
  tallyDimensions: TallyDimension[];
  boardEnabled: boolean;
  boardVisibility: BoardVisibility;
  boardReveal: BoardReveal;
  boardShowAward: boolean;
  boardShowRunningOrder: boolean;
  boardSlug: string | null;
  boardPath: string | null;
  juryCount: number;
  /** Whether any tier has a band. Without one, a festival scores and awards nothing. */
  scaleIsBanded: boolean;
  updatedAt: string | null;
}

export interface JuryMember {
  id: string;
  fullName: string;
  email: string;
  title: string | null;
  status: JuryStatus;
  isChair: boolean;
  /** Empty means the whole festival. */
  categoryIds: string[];
  categoryNames: string[];
  sortOrder: number;
  hasAccount: boolean;
  invitedAt: string | null;
  acceptedAt: string | null;
  invitationPath: string | null;
}

export interface JudgeScore {
  criterionId: string;
  score: string;
}

/** One act as a judge's tablet shows it. No participants — see ADR-0013. */
export interface JuryTask {
  submissionId: string;
  number: number;
  title: string;
  categoryId: string;
  categoryName: string | null;
  disciplineName: string | null;
  ageCategoryName: string | null;
  participationFormatName: string | null;
  organization: string | null;
  status: ScoringStatus;
  criteria: Criterion[];
  myScores: JudgeScore[];
  myComment: string | null;
  myTotal: string | null;
  submittedAt: string | null;
  canScore: boolean;
  maxTotal: string;
}

/**
 * One festival this account judges.
 *
 * The judge's own list, and the only one they can read: the organizer's festival
 * endpoint is staff-only, and a jury member is a guest of the organization rather
 * than an employee of it.
 */
export interface JurySeat {
  competitionId: string;
  title: string;
  onlineJudging: boolean;
  isChair: boolean;
  categoryNames: string[];
  startsOn: string | null;
  endsOn: string | null;
  venue: string | null;
  /** Acts this judge still owes a sheet for. */
  pendingCount: number;
  /** Whether the host has an act open right now. */
  hasOpenAct: boolean;
}

/** One act on the host's screen, in the order the hall will hear it. */
export interface RunningOrderEntry {
  submissionId: string;
  number: number;
  title: string;
  categoryName: string | null;
  disciplineName: string | null;
  ageCategoryName: string | null;
  organization: string | null;
  status: ScoringStatus;
  submittedCount: number;
  expectedJudges: number;
  score: string | null;
  awardLabel: string | null;
}

/** What pressing «Перенести в протоколы» actually did. */
export interface TallyApplication {
  rowsChanged: number;
  protocolsCreated: number;
  /** Genres with no protocol open — nowhere for the push to land. */
  missingProtocols: string[];
}

export interface Scorecard {
  juryMemberId: string;
  juryMemberName: string;
  scores: JudgeScore[];
  total: string;
  comment: string | null;
  submittedAt: string | null;
  submitted: boolean;
}

export interface PerformanceTally {
  submissionId: string;
  number: number;
  title: string;
  organization: string | null;
  score: string | null;
  maxScore: string;
  awardCode: string | null;
  awardLabel: string | null;
  submittedCount: number;
  expectedJudges: number;
  status: ScoringStatus;
  scorecards: Scorecard[];
}

export interface TallyGroup {
  key: string;
  heading: string;
  categoryId: string | null;
  tallies: PerformanceTally[];
}

export interface TallySheet {
  competitionId: string;
  groups: TallyGroup[];
  aggregation: AggregationMethod;
  scaleIsBanded: boolean;
  /** Acts that scored but fell into no band — the organizer's warning list. */
  unawardedCount: number;
}

export interface ScoringState {
  submissionId: string;
  status: ScoringStatus;
  openedAt: string | null;
  closedAt: string | null;
}

export interface BoardJudge {
  name: string;
  total: string | null;
}

export interface BoardEntry {
  number: number;
  title: string;
  organization: string | null;
  categoryName: string | null;
  ageCategoryName: string | null;
  status: ScoringStatus;
  score: string | null;
  maxScore: string;
  awardLabel: string | null;
  submittedCount: number;
  expectedJudges: number;
  judges: BoardJudge[];
}

export interface Board {
  competitionTitle: string;
  visibility: BoardVisibility;
  reveal: BoardReveal;
  showAward: boolean;
  current: BoardEntry | null;
  recent: BoardEntry[];
}

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------

export interface CriterionInput {
  /** Present for an existing criterion. Sending it back is what keeps marks attached. */
  id?: string | undefined;
  name: string;
  maxScore: string;
  weight: string;
  sortOrder: number;
  description?: string | null | undefined;
}

export interface CriteriaInput {
  competitionId: string;
  scope: JudgingScope;
  targetId: string;
  criteria: CriterionInput[];
}

export interface AwardTierInput {
  code?: string | undefined;
  label: string;
  minScore?: string | null | undefined;
  maxScore?: string | null | undefined;
  sortOrder: number;
}

export interface AwardScaleInput {
  competitionId: string;
  tiers: AwardTierInput[];
}

export interface ScoringRulesInput {
  competitionId: string;
  aggregation: AggregationMethod;
  dropHighest: boolean;
  dropLowest: boolean;
}

export interface TallyScopeInput {
  competitionId: string;
  dimensions: TallyDimension[];
}

export interface BoardInput {
  competitionId: string;
  enabled: boolean;
  visibility: BoardVisibility;
  reveal: BoardReveal;
  showAward: boolean;
  showRunningOrder: boolean;
}

export interface InviteJuryInput {
  competitionId: string;
  fullName: string;
  email: string;
  title?: string | null | undefined;
  isChair: boolean;
  categoryIds: string[];
}

export interface UpdateJuryInput {
  memberId: string;
  fullName: string;
  email: string;
  title?: string | null | undefined;
  isChair: boolean;
}

export interface AssignJuryInput {
  memberId: string;
  categoryIds: string[];
}

export interface ScoringStateInput {
  competitionId: string;
  submissionId: string;
  closePrevious?: boolean | undefined;
}

export interface SubmitScorecardInput {
  competitionId: string;
  submissionId: string;
  scores: Record<string, string>;
  comment?: string | null | undefined;
}

// ---------------------------------------------------------------------------
// Presentation helpers
// ---------------------------------------------------------------------------

export const AGGREGATION_LABELS: Record<AggregationMethod, string> = {
  AVERAGE: "Среднее по судьям",
  SUM: "Сумма баллов судей",
};

export const DIMENSION_LABELS: Record<TallyDimension, string> = {
  CATEGORY: "Жанр",
  DISCIPLINE: "Номинация",
  AGE_CATEGORY: "Возрастная категория",
  PARTICIPATION_FORMAT: "Форма участия",
};

export const VISIBILITY_LABELS: Record<BoardVisibility, string> = {
  PER_JUDGE: "Оценки каждого судьи",
  TOTAL_ONLY: "Только итоговый балл",
};

export const REVEAL_LABELS: Record<BoardReveal, string> = {
  IMMEDIATE: "Сразу, как судья отправил",
  AFTER_CLOSE: "После закрытия выступления",
};

export const JURY_STATUS_LABELS: Record<JuryStatus, string> = {
  INVITED: "Приглашён",
  ACTIVE: "Судит",
  REVOKED: "Отозван",
};

export const SCORING_STATUS_LABELS: Record<ScoringStatus, string> = {
  PENDING: "Не начато",
  OPEN: "Идёт оценка",
  CLOSED: "Закрыто",
};

/**
 * A score as a number, for drawing only.
 *
 * Never use the result to decide anything — comparisons and sums belong on the server,
 * where the value is still a decimal.
 */
export function scoreToNumber(value: string | null | undefined): number {
  const parsed = Number(value ?? "");
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * `9.50` reads better as `9,5` in a hall and on a Russian screen.
 *
 * A missing score is a dash, never a zero: a zero is a panel that judged the act and
 * thought little of it, and the two must not look the same on a board.
 */
export function formatScore(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  // Trailing zeros only after a decimal point — `100` must stay `100`.
  const trimmed = value.includes(".") ? value.replace(/0+$/, "").replace(/\.$/, "") : value;
  return trimmed.replace(".", ",");
}

/** "90–100", "от 95", "до 59,99", or a dash when the tier has no band at all. */
export function formatBand(tier: Pick<AwardTier, "minScore" | "maxScore">): string {
  const from = tier.minScore == null ? null : formatScore(tier.minScore);
  const to = tier.maxScore == null ? null : formatScore(tier.maxScore);
  if (from != null && to != null) return `${from}–${to}`;
  if (from != null) return `от ${from}`;
  if (to != null) return `до ${to}`;
  return "—";
}

/**
 * The genres whose criteria are still missing.
 *
 * The one check worth doing in the browser: an organizer who switches online judging
 * on and never opens this section has a panel with nothing to fill in, and they find
 * out on the day.
 */
export function genresWithoutCriteria(setup: JudgingSetup): Nomination[] {
  const configured = new Set(
    setup.criteriaSets.filter((item) => item.scope === "CATEGORY").map((item) => item.targetId),
  );
  return setup.nominations.filter((item) => !configured.has(item.categoryId));
}

/** Whether the festival is ready to be judged online, and what is missing if not. */
export function judgingReadiness(setup: JudgingSetup): {
  ready: boolean;
  problems: string[];
} {
  const problems: string[] = [];
  if (setup.nominations.length === 0) {
    problems.push("Не заданы жанры — сначала добавьте их в разделе «Жанры и номинации».");
  } else {
    const missing = genresWithoutCriteria(setup);
    if (missing.length > 0) {
      problems.push(`Нет критериев для жанров: ${missing.map((item) => item.name).join(", ")}.`);
    }
  }
  if (!setup.scaleIsBanded) {
    problems.push("В шкале наград не заданы диапазоны баллов — награда не определится.");
  }
  if (setup.juryCount === 0) {
    problems.push("В жюри никого нет — пригласите судей во вкладке «Жюри».");
  }
  return { ready: problems.length === 0, problems };
}
