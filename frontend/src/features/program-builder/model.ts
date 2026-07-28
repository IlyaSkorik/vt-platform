/**
 * Programme constructor domain types (organizer side).
 *
 * A programme is a **table**: one row per item, and a fixed set of columns it can carry.
 * The backend owns the order and recomputes the timetable on every write, so these types
 * mirror that shape exactly and the client never recalculates a start time itself.
 *
 * Columns are also the unit a public link is cut along — publishing an edition means
 * choosing which of them its reader sees.
 */

/** What a slot is. Only the first two are creatable from the UI today. */
export type ProgramItemKind =
  | "PERFORMANCE"
  | "BREAK"
  | "OPENING"
  | "AWARD"
  | "MASTER_CLASS"
  | "TECHNICAL";

/** A column of the programme table. Mirrors the backend's `ProgramColumn`. */
export type ProgramColumnKey =
  | "POSITION"
  | "TIME"
  | "PARTICIPANT"
  | "TITLE"
  | "DURATION"
  | "NOMINATION"
  | "DISCIPLINE"
  | "PARTICIPANT_GROUP"
  | "AGE_CATEGORY"
  | "PARTICIPATION_FORMAT"
  | "TEACHERS"
  | "ORGANIZATION"
  | "COMMENT";

/** One column: its stable key and the header the backend prints it under. */
export interface ProgramColumn {
  key: ProgramColumnKey;
  label: string;
}

/** Where one item sits on the timeline (computed by the backend). */
export interface SchedulePosition {
  position: number;
  offsetSeconds: number;
  /** The item's length plus any buffer — the space it occupies in the day. */
  slotSeconds: number;
  startsAt: string | null;
  endsAt: string | null;
}

/** One slot of the running order. */
export interface ProgramItem {
  id: string;
  kind: ProgramItemKind;
  title: string;
  durationSeconds: number;
  schedule: SchedulePosition;
  submissionId: string | null;
  leadParticipant: string | null;
  participants: string[];
  teachers: string[];
  nomination: string | null;
  discipline: string | null;
  ageCategory: string | null;
  participantGroup: string | null;
  participationFormat: string | null;
  organization: string | null;
  /** The applicant's note for the organizers about this act. */
  comment: string | null;
  /** True when the act behind this slot is no longer competing. */
  missingPerformance: boolean;
}

/** A named public edition: the columns it shows, and the path its link points at. */
export interface ProgramShare {
  id: string;
  name: string;
  slug: string;
  path: string;
  /** The columns this link publishes — what the edition is for. */
  columns: ProgramColumn[];
  itemCount: number;
  /** An edition with no fixed row selection keeps following the whole programme. */
  coversWholeProgram: boolean;
  createdAt: string | null;
}

/** One programme in full, with its recomputed timetable. */
export interface Program {
  id: string;
  competitionId: string;
  nominationId: string | null;
  name: string;
  bufferSeconds: number;
  startsAt: string | null;
  items: ProgramItem[];
  shares: ProgramShare[];
  /** Every column the table can carry — the header, and what a link may be cut to. */
  availableColumns: ProgramColumn[];
  totalSeconds: number;
  endsAt: string | null;
  createdAt: string;
  updatedAt: string;
  version: number;
}

/** A programme as it appears in the list on the left. */
export interface ProgramSummary {
  id: string;
  competitionId: string;
  nominationId: string | null;
  name: string;
  bufferSeconds: number;
  startsAt: string | null;
  itemCount: number;
  performanceCount: number;
  totalSeconds: number;
  shareCount: number;
  createdAt: string;
  updatedAt: string;
}

/** A competing act that has no slot in this programme yet. */
export interface ProgramCandidate {
  submissionId: string;
  title: string;
  durationSeconds: number;
  nomination: string | null;
  discipline: string | null;
  ageCategory: string | null;
  participantGroup: string | null;
  participationFormat: string | null;
  participants: string[];
  teachers: string[];
  organization: string | null;
  comment: string | null;
}

export interface CreateProgramInput {
  competitionId: string;
  name: string;
  nominationId?: string | null;
  bufferSeconds?: number;
  startsAt?: string | null;
}

export interface UpdateProgramInput {
  name?: string;
  bufferSeconds?: number;
  startsAt?: string | null;
}

export interface AddBlockInput {
  title: string;
  durationSeconds: number;
  kind?: ProgramItemKind;
  position?: number;
}

export interface CreateShareInput {
  name: string;
  /** The columns this link publishes. Empty falls back to the backend's defaults. */
  columns?: ProgramColumnKey[];
  /** Optionally narrow the rows too. Empty publishes every row, now and later. */
  itemIds?: string[];
}

/** The buffer presets the constructor offers (seconds). */
export const BUFFER_PRESETS = [0, 30, 45, 60, 90, 120] as const;

/** What a public link shows when the organizer has not chosen otherwise. */
export const DEFAULT_SHARE_COLUMNS: ProgramColumnKey[] = [
  "POSITION",
  "TIME",
  "PARTICIPANT",
  "TITLE",
];

/**
 * One cell of the organizer's table.
 *
 * The same mapping the backend applies when it renders a published edition, so the
 * constructor and every public link show identical text for identical data. A block has
 * no participant or age category and gets a blank rather than a placeholder that would
 * read like missing data.
 */
export function itemCell(
  item: ProgramItem,
  column: ProgramColumnKey,
  format: { clock: (iso: string | null) => string; duration: (seconds: number) => string },
): string {
  switch (column) {
    case "POSITION":
      return String(item.schedule.position);
    case "TIME":
      return format.clock(item.schedule.startsAt);
    case "PARTICIPANT":
      return item.leadParticipant ?? "";
    case "TITLE":
      return item.title;
    case "DURATION":
      return format.duration(item.durationSeconds);
    case "NOMINATION":
      return item.nomination ?? "";
    case "DISCIPLINE":
      return item.discipline ?? "";
    case "PARTICIPANT_GROUP":
      return item.participantGroup ?? "";
    case "AGE_CATEGORY":
      return item.ageCategory ?? "";
    case "PARTICIPATION_FORMAT":
      return item.participationFormat ?? "";
    case "TEACHERS":
      return item.teachers.join(", ");
    case "ORGANIZATION":
      return item.organization ?? "";
    case "COMMENT":
      return item.comment ?? "";
    default:
      return "";
  }
}

/** Human label for a slot kind. */
export const ITEM_KIND_LABELS: Record<ProgramItemKind, string> = {
  PERFORMANCE: "Выступление",
  BREAK: "Перерыв",
  OPENING: "Открытие",
  AWARD: "Награждение",
  MASTER_CLASS: "Мастер-класс",
  TECHNICAL: "Технический блок",
};

/**
 * Move one item within a list, returning the new complete order.
 *
 * The reorder endpoint takes the whole order rather than a move instruction, so this
 * is the one place order is manipulated: the caller sends what the organizer sees.
 */
export function moveItem<T>(items: readonly T[], from: number, to: number): T[] {
  const next = [...items];
  if (from < 0 || from >= next.length || to < 0 || to >= next.length || from === to) {
    return next;
  }
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved as T);
  return next;
}
