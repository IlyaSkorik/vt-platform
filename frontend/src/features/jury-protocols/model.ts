/**
 * Jury protocol domain types (organizer side).
 *
 * A protocol is a **table**: one row per act, in the order they performed, and a fixed set
 * of columns it can carry. The backend owns the order, the numbers and the wording of every
 * award, so these types mirror that shape exactly and the client never invents a label.
 *
 * Two things about the shape are worth knowing before reading the UI code:
 *
 * - **`award` and `awardLabel` travel together.** `award` is the enum name the client sends
 *   back; `awardLabel` is the wording to render. The client never maps one to the other from
 *   a table of its own, because the same wording has to appear on the diploma and in the
 *   letter, and a second copy of it here is how those come to disagree.
 * - **`hasUnpublishedChanges` is the whole publish story.** Awards stay editable after
 *   publication and those edits reach nobody until the next publish, so this flag is what
 *   the screen has to be honest about.
 */

/** A column of the protocol table. Mirrors the backend's `ProtocolColumn`. */
export type ProtocolColumnKey =
  | "POSITION"
  | "PARTICIPANT"
  | "TITLE"
  | "AWARD"
  | "NOMINATION"
  | "DISCIPLINE"
  | "PARTICIPANT_GROUP"
  | "AGE_CATEGORY"
  | "PARTICIPATION_FORMAT"
  | "TEACHERS"
  | "ORGANIZATION";

/** One column: its stable key and the header it is printed under. */
export interface ProtocolColumn {
  key: ProtocolColumnKey;
  label: string;
}

/**
 * What the jury awarded. Mirrors the backend's `AwardKind`.
 *
 * There is no place and no score anywhere in this vocabulary: a result is a degree and
 * nothing else, which is why the list is closed and why nothing here is ordered by points.
 */
export type AwardKind =
  | "GRAND_PRIX"
  | "GRAND_PRIX_NOMINEE"
  | "LAUREATE_I"
  | "LAUREATE_II"
  | "LAUREATE_III"
  | "DIPLOMANT_I"
  | "DIPLOMANT_II"
  | "DIPLOMANT_III"
  | "PARTICIPANT";

/** Whether the results have left the organization. */
export type ProtocolStatus = "DRAFT" | "PUBLISHED";

/**
 * One award as the dropdown offers it.
 *
 * Served by the API rather than hard-coded here: the wording appears on a protocol, on a
 * diploma and in a letter, so it has exactly one home and this is a copy of it, not a
 * source. `seniority` orders the list (0 = Гран-при) and is not a place.
 */
export interface AwardOption {
  value: AwardKind;
  label: string;
  seniority: number;
}

/** One row of the jury's table: the act, and what it won. */
export interface ProtocolRow {
  id: string;
  /** The number the act performed under — copied from the programme, then its own. */
  number: number;
  submissionId: string;
  title: string;
  /** `null` while the jury has not decided. A permanent, legitimate state. */
  award: AwardKind | null;
  /** The wording for {@link award}, straight from the backend. */
  awardLabel: string | null;
  leadParticipant: string | null;
  participants: string[];
  teachers: string[];
  nomination: string | null;
  discipline: string | null;
  ageCategory: string | null;
  participantGroup: string | null;
  participationFormat: string | null;
  organization: string | null;
  /** True when the entry behind this row is gone from the competition entirely. */
  missingPerformance: boolean;
}

/** One protocol in full. */
export interface Protocol {
  id: string;
  competitionId: string;
  nominationId: string;
  nomination: string | null;
  competitionTitle: string | null;
  name: string;
  status: ProtocolStatus;
  rows: ProtocolRow[];
  /** Every column the table can carry — the header, and what the page may be cut to. */
  availableColumns: ProtocolColumn[];
  /** The columns the published page shows. */
  publicColumns: ProtocolColumn[];
  /** The award vocabulary, so the dropdown is served and not duplicated. */
  awardOptions: AwardOption[];
  /** How many times these results have been published (0 = never). */
  revision: number;
  slug: string | null;
  /** The client-side path the published page lives at, or `null` before publication. */
  path: string | null;
  publishedAt: string | null;
  /** True when the table has been edited since the revision that is currently public. */
  hasUnpublishedChanges: boolean;
  seededFromProgramId: string | null;
  createdAt: string;
  updatedAt: string;
  version: number;
}

/** A protocol as it appears in the list of nominations on the left. */
export interface ProtocolSummary {
  id: string;
  competitionId: string;
  nominationId: string;
  nomination: string | null;
  name: string;
  status: ProtocolStatus;
  rowCount: number;
  /** How many rows the jury has actually decided — the progress the list shows. */
  decidedCount: number;
  revision: number;
  slug: string | null;
  path: string | null;
  publishedAt: string | null;
  hasUnpublishedChanges: boolean;
  createdAt: string;
  updatedAt: string;
}

/** What one publication did, beyond changing the protocol's status. */
export interface PublicationResult {
  protocol: Protocol;
  diplomasAwarded: number;
  diplomasCreated: number;
  /**
   * Awarded rows whose diploma could not be resolved — normally a nomination with no
   * diploma template assigned. Those participants have a result and no document, so this
   * is the one number the confirmation must not bury.
   */
  diplomasMissing: number;
  lettersSent: number;
  lettersSkipped: number;
}

/** A competing act of this nomination that has no row in the protocol yet. */
export interface ProtocolCandidate {
  submissionId: string;
  title: string;
  nomination: string | null;
  discipline: string | null;
  ageCategory: string | null;
  participantGroup: string | null;
  participationFormat: string | null;
  participants: string[];
  teachers: string[];
  organization: string | null;
}

export interface CreateProtocolInput {
  competitionId: string;
  nominationId: string;
  name?: string;
  columns?: ProtocolColumnKey[];
  /** Seed the rows from the nomination's running order. On by default. */
  seed?: boolean;
}

export interface UpdateProtocolInput {
  name?: string;
  columns?: ProtocolColumnKey[];
}

/** One result being written. `award: null` clears it. */
export interface AwardEntry {
  rowId: string;
  award: AwardKind | null;
}

export interface PublishProtocolInput {
  /** Which columns the public page shows — decided in the publish dialog. */
  columns?: ProtocolColumnKey[];
  /** Whether to write to the participants. On by default. */
  notify?: boolean;
}

/**
 * What the publish dialog starts with when the organizer has published nothing yet.
 *
 * Deliberately narrow, mirroring the backend's default: a public results page must never
 * widen by accident to a child's school and teacher.
 */
export const DEFAULT_PUBLIC_COLUMNS: ProtocolColumnKey[] = [
  "POSITION",
  "PARTICIPANT",
  "TITLE",
  "AWARD",
];

/** Statuses as the workspace names them. */
export const PROTOCOL_STATUS_LABELS: Record<ProtocolStatus, string> = {
  DRAFT: "Черновик",
  PUBLISHED: "Опубликован",
};

/**
 * How many rows still need a result.
 *
 * Not a blocker — a protocol with blanks is publishable, because an act that did not appear
 * is a blank line — but it is what the jury works down, so the screen shows it.
 */
export function undecidedCount(protocol: Protocol): number {
  return protocol.rows.filter((row) => row.award == null).length;
}

/** Whether pressing "Опубликовать" would do anything at all. */
export function canPublish(protocol: Protocol): boolean {
  return protocol.rows.some((row) => row.award != null);
}

/**
 * One cell of the organizer's table.
 *
 * The same mapping the backend applies when it renders the published page, so the jury's
 * screen and the public protocol show identical text for identical data. A row whose entry
 * has been withdrawn renders blanks rather than a placeholder that would read like data.
 */
export function rowCell(row: ProtocolRow, column: ProtocolColumnKey): string {
  switch (column) {
    case "POSITION":
      return String(row.number);
    case "PARTICIPANT":
      return row.leadParticipant ?? "";
    case "TITLE":
      return row.title;
    case "AWARD":
      return row.awardLabel ?? "";
    case "NOMINATION":
      return row.nomination ?? "";
    case "DISCIPLINE":
      return row.discipline ?? "";
    case "PARTICIPANT_GROUP":
      return row.participantGroup ?? "";
    case "AGE_CATEGORY":
      return row.ageCategory ?? "";
    case "PARTICIPATION_FORMAT":
      return row.participationFormat ?? "";
    case "TEACHERS":
      return row.teachers.join(", ");
    case "ORGANIZATION":
      return row.organization ?? "";
    default:
      return "";
  }
}

/**
 * Move one row within a list, returning the new complete order.
 *
 * The reorder endpoint takes the whole order rather than a move instruction, so this is the
 * one place order is manipulated: the caller sends what the organizer sees.
 */
export function moveRow<T>(rows: readonly T[], from: number, to: number): T[] {
  const next = [...rows];
  if (from < 0 || from >= next.length || to < 0 || to >= next.length || from === to) {
    return next;
  }
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved as T);
  return next;
}
