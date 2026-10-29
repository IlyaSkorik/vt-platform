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
  | "PARTICIPANT_COUNT"
  | "AGE_CATEGORY"
  | "PARTICIPATION_FORMAT"
  | "TEACHERS"
  | "ORGANIZATION"
  | "CONTACTS"
  | "COMMENT";

/**
 * A column key: a built-in one, or `custom:<uuid>` for one the organizer added.
 *
 * Typed as a union with `string` on purpose — the set of custom keys is open, and the
 * client never needs to know them, only pass them back.
 */
export type ColumnKey = ProgramColumnKey | (string & {});

/** One column: its stable key, its header, and whether the organizer added it. */
export interface ProgramColumn {
  key: ColumnKey;
  label: string;
  /** Only custom columns can be renamed, removed, or filled in by hand. */
  custom: boolean;
}

/** How far one slot has got on the day itself. */
export type ProgramItemProgress = "PENDING" | "ON_STAGE" | "PERFORMED" | "SKIPPED" | "CANCELLED";

/**
 * What each progress state is called on screen.
 *
 * «Пропущен» and «Отменён» are kept apart because the day keeps them apart: the first is
 * an act the host stepped over and may come back to, the second is one that is not
 * happening — and the organizer reading this table needs to know which.
 */
export const PROGRESS_LABELS: Record<ProgramItemProgress, string> = {
  PENDING: "Ожидает",
  ON_STAGE: "На сцене",
  PERFORMED: "Выступил",
  SKIPPED: "Пропущен",
  CANCELLED: "Отменён",
};

/**
 * Where one item sits on the timeline (computed by the backend).
 *
 * `position` is the row's place in the running order (1..N, always contiguous). It is
 * *not* the participant's number — see {@link ProgramItem.number}.
 */
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
  /**
   * The slot's number in the programme.
   *
   * Follows the running order while the programme is unpublished, and is fixed to the
   * slot from the first public link onwards — so a rearranged published programme
   * legitimately reads 2, 3, 5, 4.
   */
  number: number;
  durationSeconds: number;
  schedule: SchedulePosition;
  submissionId: string | null;
  participants: string[];
  /**
   * How many people stand on stage — the headcount, not `participants.length`.
   *
   * A collective is one entry row and the number its applicant typed on the form; a solo
   * is one row and one person. `0` for a block, which puts nobody on stage.
   */
  participantCount: number;
  teachers: string[];
  /** Phones to ring about this act: its teachers', or the applicant's if none has one. */
  contacts: string[];
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
  /** Hand-filled values, keyed by custom column key. */
  customValues: Record<string, string>;
  /** How far this slot has got on the day (the host drives it). */
  progress: ProgramItemProgress;
}

/**
 * An axis a generated running order can be grouped along.
 *
 * These are the facets a festival day is actually blocked out by — the audience sees all
 * of «Эстрадный вокал» together, and within it all of «7-9 лет» together. The *order* of
 * the chosen axes is the shape of the day: nomination-then-age builds a different
 * festival from age-then-nomination.
 */
export type GroupingAxis =
  | "NOMINATION"
  | "DISCIPLINE"
  | "AGE_CATEGORY"
  | "PARTICIPANT_GROUP"
  | "PARTICIPATION_FORMAT"
  | "ORGANIZATION";

/** How acts are ordered inside one group. */
export type PerformanceOrder =
  | "AGE_ASC"
  | "AGE_DESC"
  | "TITLE"
  | "PARTICIPANT"
  | "ORGANIZATION"
  | "DURATION_ASC"
  | "DURATION_DESC";

/**
 * When the generator puts a break in.
 *
 * One rule, not a set of them: an отделение is simply what lies between two breaks, so
 * "перерыв каждые 90 минут" and "отделение не длиннее 90 минут" are one instruction.
 */
export type BreakRule = "NONE" | "EVERY_DURATION" | "EVERY_COUNT" | "BETWEEN_GROUPS";

/**
 * What each grouping axis is called on the settings form.
 *
 * **Display vocabulary.** The code's `NOMINATION` is shown to people as «Жанр», and
 * `DISCIPLINE` as «Номинация» — the identifiers keep the older names because they run
 * through the API contract and every stored snapshot, while the words the platform
 * speaks to organizers changed. These labels lagged behind that change, so the generator
 * offered to group «по номинации» and grouped by genre: the dialog and the table beside
 * it named the same axis two different things.
 *
 * Word for word the backend's `COLUMN_LABELS` (`apps/programs/domain/value_objects.py`),
 * which is what the programme's own column headers come from.
 */
export const GROUPING_AXIS_LABELS: Record<GroupingAxis, string> = {
  NOMINATION: "Жанр",
  DISCIPLINE: "Номинация",
  AGE_CATEGORY: "Возрастная категория",
  PARTICIPANT_GROUP: "Состав участников",
  PARTICIPATION_FORMAT: "Формат участия",
  ORGANIZATION: "Организация",
};

export const PERFORMANCE_ORDER_LABELS: Record<PerformanceOrder, string> = {
  AGE_ASC: "Младшие вперёд",
  AGE_DESC: "Старшие вперёд",
  TITLE: "По названию номера",
  PARTICIPANT: "По фамилии участника",
  ORGANIZATION: "По организации",
  DURATION_ASC: "Короткие вперёд",
  DURATION_DESC: "Длинные вперёд",
};

export const BREAK_RULE_LABELS: Record<BreakRule, string> = {
  NONE: "Без перерывов",
  EVERY_DURATION: "Через каждые N минут",
  EVERY_COUNT: "Через каждые N номеров",
  BETWEEN_GROUPS: "На стыке групп",
};

/** The axes the generator groups by when the organizer states nothing. */
export const DEFAULT_GROUPING: GroupingAxis[] = ["NOMINATION", "DISCIPLINE", "AGE_CATEGORY"];

/** The order the axes are offered in — the order a programme is usually read along. */
export const GROUPING_AXES: GroupingAxis[] = [
  "NOMINATION",
  "DISCIPLINE",
  "AGE_CATEGORY",
  "PARTICIPANT_GROUP",
  "PARTICIPATION_FORMAT",
  "ORGANIZATION",
];

/**
 * The rules a programme was generated from, as the backend stores and returns them.
 *
 * The same shape goes out on `POST .../items/arrange` and comes back on the programme,
 * so the dialog reopens on exactly what produced the running order on screen.
 */
export interface ArrangementSettings {
  grouping: GroupingAxis[];
  orderWithinGroup: PerformanceOrder;
  breakRule: BreakRule;
  breakAfterSeconds: number;
  breakAfterItems: number;
  breakTitle: string | null;
  breakDurationSeconds: number | null;
  /** How many slots must separate two acts of the same participant. 0 turns it off. */
  repeatGap: number;
  openingTitle: string | null;
  openingDurationSeconds: number | null;
  awardTitle: string | null;
  awardDurationSeconds: number | null;
}

/**
 * The body of a generation request. Every field is optional, and an **empty body means
 * "the rules this programme was last built from"** — which is what makes «Пересобрать» a
 * button without a form. A body that is present is read as complete.
 */
export type ArrangeProgramInput = Partial<ArrangementSettings>;

/** What a fresh generator dialog opens on. */
export const DEFAULT_ARRANGEMENT: ArrangementSettings = {
  grouping: DEFAULT_GROUPING,
  orderWithinGroup: "AGE_ASC",
  breakRule: "NONE",
  breakAfterSeconds: 5400,
  breakAfterItems: 20,
  breakTitle: "Перерыв",
  breakDurationSeconds: 600,
  repeatGap: 0,
  openingTitle: null,
  openingDurationSeconds: null,
  awardTitle: null,
  awardDurationSeconds: null,
};

/**
 * Turn the dialog's state into a request body.
 *
 * The two places the form and the contract differ: a rule of `NONE` carries no break,
 * and a service block is switched on by *naming* it — so a block the organizer left off
 * sends neither its title nor its duration rather than sending nulls the API would read
 * as "a block called null".
 */
export function arrangeInput(settings: ArrangementSettings): ArrangeProgramInput {
  const input: ArrangeProgramInput = {
    grouping: settings.grouping,
    orderWithinGroup: settings.orderWithinGroup,
    breakRule: settings.breakRule,
    repeatGap: settings.repeatGap,
  };
  if (settings.breakRule !== "NONE") {
    input.breakTitle = settings.breakTitle ?? "Перерыв";
    input.breakDurationSeconds = settings.breakDurationSeconds ?? 600;
    if (settings.breakRule === "EVERY_DURATION") {
      input.breakAfterSeconds = settings.breakAfterSeconds;
    }
    if (settings.breakRule === "EVERY_COUNT") {
      input.breakAfterItems = settings.breakAfterItems;
    }
  }
  if (settings.openingTitle) {
    input.openingTitle = settings.openingTitle;
    input.openingDurationSeconds = settings.openingDurationSeconds ?? 900;
  }
  if (settings.awardTitle) {
    input.awardTitle = settings.awardTitle;
    input.awardDurationSeconds = settings.awardDurationSeconds ?? 1800;
  }
  return input;
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
  /** Whether this link may drive the running order on the day — the host's edition. */
  controlsRunningOrder: boolean;
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
  /**
   * Whether numbers are fixed to their slots.
   *
   * `false` while the programme is being assembled: numbers follow the order and a
   * reorder renumbers freely. The first published link flips this for good.
   */
  numbersFrozen: boolean;
  numbersFrozenAt: string | null;
  totalSeconds: number;
  endsAt: string | null;
  /** The rules this programme was generated from — `null` if it was only built by hand. */
  arrangement: ArrangementSettings | null;
  /**
   * Whether the last «Пересобрать» can still be put back.
   *
   * True only between a rebuild and the undo that consumes it, and never for a
   * published programme — its numbers have been told to participants and may not move.
   * The server owns this: the replaced rows are still on disk, and only it knows
   * whether they are still addressable.
   */
  canUndoArrange: boolean;
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

/**
 * What came of announcing one published edition to the people in it.
 *
 * Three numbers, because an organizer who sent 40 letters for 47 acts needs to know
 * which gap they are looking at. `skipped` is acts whose applicant has no address on
 * the platform — nobody's mistake, and nothing a second attempt would fix.
 */
export interface ProgramAnnouncement {
  notified: number;
  acts: number;
  skipped: number;
}

export interface AnnounceShareInput {
  shareId: string;
  /** A line of the organizer's own above the running order. Optional. */
  note?: string;
}

export interface CreateShareInput {
  name: string;
  /** The columns this link publishes. Empty falls back to the backend's defaults. */
  columns?: ColumnKey[];
  /** Optionally narrow the rows too. Empty publishes every row, now and later. */
  itemIds?: string[];
  /** Make this the host's edition: its holder may drive the running order. */
  controlsRunningOrder?: boolean;
}

/**
 * The buffer presets the constructor offers (seconds).
 *
 * Twenty seconds is the shortest one worth having: it is a soloist walking off while the
 * next walks on, which is the gap a tightly run festival actually leaves — anything
 * smaller is not a changeover, and the schedule it produces does not survive the day.
 */
export const BUFFER_PRESETS = [0, 20, 30, 45, 60, 90, 120] as const;

/** What a public link shows when the organizer has not chosen otherwise. */
export const DEFAULT_SHARE_COLUMNS: ProgramColumnKey[] = [
  "POSITION",
  "TIME",
  "PARTICIPANT",
  "TITLE",
];

/**
 * What a printed programme starts with.
 *
 * Wider than a screen's default — paper has room and a printed running order is usually
 * the one people work from — but not everything: a thirteen-column page is unreadable.
 */
export const DEFAULT_EXPORT_COLUMNS: ProgramColumnKey[] = [
  "POSITION",
  "TIME",
  "PARTICIPANT",
  "TITLE",
  "DURATION",
  "ORGANIZATION",
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
  column: ColumnKey,
  format: { clock: (iso: string | null) => string; duration: (seconds: number) => string },
): string {
  // A column the organizer added: whatever they typed into this row, or nothing.
  if (column.startsWith("custom:")) {
    return item.customValues[column] ?? "";
  }
  switch (column) {
    case "POSITION": {
      // The participant's permanent number, not the row's index — and nothing at all for
      // a break: it is a gap in the running order rather than an act with a number.
      const number = itemNumber(item);
      return number === null ? "" : String(number);
    }
    case "TIME":
      return format.clock(item.schedule.startsAt);
    case "PARTICIPANT":
      // Everyone the entry listed, not just the first of them — a duet is two performer
      // rows and both names belong here. The headcount has its own column.
      return item.participants.join(", ");
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
    case "PARTICIPANT_COUNT":
      // Blank rather than "0" for a slot that puts nobody on stage: a break with a
      // headcount of zero reads like an act nobody turned up to.
      return item.participantCount > 0 ? String(item.participantCount) : "";
    case "AGE_CATEGORY":
      return item.ageCategory ?? "";
    case "PARTICIPATION_FORMAT":
      return item.participationFormat ?? "";
    case "TEACHERS":
      return item.teachers.join(", ");
    case "ORGANIZATION":
      return item.organization ?? "";
    case "CONTACTS":
      return item.contacts.join(", ");
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

/**
 * Move a contiguous run of items to `to`, returning the new complete order.
 *
 * `to` is an **insertion index into the list as it is now**: the run lands in front of
 * whatever currently sits there, and `items.length` means the very end. Counted that way
 * because that is what a drop between two rows means — and the run has to be lifted out
 * before it can be put back, which shifts every index past it down by its own length.
 *
 * This is {@link moveItem} generalised to a block, and the block is the point: "возьми
 * весь эстрадный вокал и подними наверх" is one gesture, not forty.
 */
export function moveBlock<T>(items: readonly T[], start: number, count: number, to: number): T[] {
  const next = [...items];
  if (start < 0 || count <= 0 || start + count > next.length || to < 0 || to > next.length) {
    return next;
  }
  // Dropped back inside itself — including on either of its own edges, which is a move
  // to where it already is.
  if (to >= start && to <= start + count) {
    return next;
  }
  const moved = next.splice(start, count);
  next.splice(to > start ? to - count : to, 0, ...moved);
  return next;
}

/** One run of consecutive slots that share a value — what a group move acts on. */
export interface ProgramGroup {
  /** Stable React key: the id of the run's first slot. */
  key: string;
  /** The header: the shared value, or a block's own title. */
  label: string;
  /** Where the run starts in the programme's order. */
  start: number;
  items: ProgramItem[];
  /** A service block is a divider between groups, never part of one. */
  standalone: boolean;
}

/**
 * The running order cut into consecutive runs of one value.
 *
 * **Consecutive, not sorted.** The order on screen is the order of the day, and grouping
 * is a reading of it rather than a rearrangement of it: if эстрадный вокал appears in two
 * places because the organizer put it there, this says so with two groups instead of
 * pretending there is one. That is also what makes a group safe to drag — a group is a
 * slice of the order, so moving it is one {@link moveBlock} and the rest of the day is
 * untouched.
 *
 * A break (or an award, or an opening) always stands alone: it is what separates one part
 * of the day from the next, and swallowing it into the group above would mean dragging
 * вокал somewhere and taking lunch along with it.
 *
 * The axis is a {@link GroupingAxis} — the same vocabulary the generator groups by, so
 * "собрать по жанрам" and "показать по жанрам" cannot drift apart.
 */
export function groupRuns(items: readonly ProgramItem[], axis: GroupingAxis): ProgramGroup[] {
  const groups: ProgramGroup[] = [];
  items.forEach((item, index) => {
    const standalone = item.kind !== "PERFORMANCE";
    const label = standalone ? item.title : groupLabel(item, axis);
    const open = groups.at(-1);
    if (open !== undefined && !open.standalone && !standalone && open.label === label) {
      open.items.push(item);
      return;
    }
    groups.push({ key: item.id, label, start: index, items: [item], standalone });
  });
  return groups;
}

/**
 * The value one slot is grouped under.
 *
 * Deliberately the same text {@link itemCell} puts in that column: the header of a group
 * and the cells under it have to read identically, or the grouping looks wrong even when
 * it is right. A slot with nothing in that column gets «—», so an act missing its age
 * category is visibly missing it rather than silently joining the group above.
 */
function groupLabel(item: ProgramItem, axis: GroupingAxis): string {
  return itemCell(item, axis, UNUSED_FORMAT) || "—";
}

/** {@link itemCell} wants a formatter; none of the grouping axes is a time or a length. */
const UNUSED_FORMAT = { clock: () => "", duration: () => "" };

/**
 * The number a person reads in the «№» column, or `null` for a slot that has none.
 *
 * The printed one once numbers are frozen, the row's own while the programme is still
 * being assembled — the same fallback {@link itemCell} renders, because a control that
 * asks "after which number?" has to mean the number the organizer is looking at.
 *
 * Service blocks — перерыв, награждение, открытие — are deliberately unnumbered, on both
 * sides: numbering a break pushes every act after it one place along, and «номер 12»
 * then means a fifteen-minute gap to whoever is holding the printed programme.
 */
export function itemNumber(item: ProgramItem): number | null {
  if (item.kind !== "PERFORMANCE") {
    return null;
  }
  return item.number || item.schedule.position;
}

/** Where a moved slot lands relative to the number it was pointed at. */
export type Placement = "before" | "after";

/**
 * The new complete order after the slot at `from` is dropped next to the slot numbered
 * `targetNumber`. `null` when nothing in the programme carries that number — the caller
 * says so rather than silently moving the act somewhere else.
 *
 * The arrows walk a slot one row at a time, which is right for a correction and hopeless
 * for the move this exists for: the act announced next is at the bottom of a forty-row
 * programme and belongs at the top *now*. Numbering, not row indexes, because a frozen
 * programme reads 2, 3, 5, 4 and the number is what everyone in the hall is holding.
 */
export function moveItemNextTo(
  items: readonly ProgramItem[],
  from: number,
  targetNumber: number,
  placement: Placement,
): ProgramItem[] | null {
  const target = items.findIndex((item) => itemNumber(item) === targetNumber);
  if (target === -1) {
    return null;
  }
  if (target === from) {
    return [...items];
  }
  // `moveItem` inserts into the list the moved slot has already left, so an index past
  // it shifts down by one. Working that out here keeps `moveItem` the single splice.
  const shift = target > from ? -1 : 0;
  return moveItem(items, from, target + shift + (placement === "after" ? 1 : 0));
}
