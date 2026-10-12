/**
 * Rearranging a published programme, without the React around it.
 *
 * The host's reorder endpoint takes the complete new order rather than a move
 * instruction, so every function here returns the whole list of item ids — or `null`
 * when the move cannot be made, which the caller reports instead of sending a running
 * order nobody asked for.
 */

import type { PublicProgramRow } from "./api";

/** Where a moved row lands relative to the number it was pointed at. */
export type Placement = "before" | "after";

/**
 * The number the host reads in the «№» column, or `null` for a row that has none.
 *
 * Falls back to the row's own place when the organizer did not publish that column: the
 * host is then counting rows down the page, and counting rows is what the fallback does.
 * The printed number is not the row's index on a published programme — numbers stay with
 * their participants through a rearrangement, which is the whole reason to read it here.
 *
 * When the column *is* published, a blank cell means the row genuinely has no number —
 * перерыв, награждение — and that is answered as `null` rather than patched up with the
 * row's index: an index that happens to equal a real act's number would make "после №5"
 * land next to the lunch break instead.
 */
export function rowNumber(
  row: PublicProgramRow,
  index: number,
  columns: readonly string[],
): number | null {
  const at = columns.indexOf("POSITION");
  if (at === -1) {
    return index + 1;
  }
  const printed = Number.parseInt(row.cells[at] ?? "", 10);
  return Number.isFinite(printed) && printed > 0 ? printed : null;
}

/**
 * The ids of every row, in order — or `null` unless all of them carry one.
 *
 * Only the host's edition sends ids; on any other the rows cannot be addressed at all,
 * and a reorder must not be attempted rather than sent with blanks in it.
 */
function idsOf(rows: readonly PublicProgramRow[]): string[] | null {
  const ids = rows.map((row) => row.id ?? "");
  return ids.some((id) => id.length === 0) ? null : ids;
}

/** The new complete order after the row at `from` moves to index `to`. */
export function moveRowTo(
  rows: readonly PublicProgramRow[],
  from: number,
  to: number,
): string[] | null {
  const ids = idsOf(rows);
  if (ids === null || from < 0 || from >= ids.length || to < 0 || to >= ids.length) {
    return null;
  }
  const [moved] = ids.splice(from, 1);
  ids.splice(to, 0, moved as string);
  return ids;
}

/**
 * The new complete order after the row at `from` is dropped next to the row numbered
 * `targetNumber`. `null` when nothing in the programme carries that number.
 *
 * This is the move the arrows cannot make: the act announced next is at the bottom of a
 * forty-row programme and belongs at the top now, and the host names where rather than
 * walking it there one row at a time.
 */
export function moveRowNextTo(
  rows: readonly PublicProgramRow[],
  columns: readonly string[],
  from: number,
  targetNumber: number,
  placement: Placement,
): string[] | null {
  const target = rows.findIndex((row, index) => rowNumber(row, index, columns) === targetNumber);
  if (target === -1) {
    return null;
  }
  if (target === from) {
    return idsOf(rows);
  }
  // The insert happens in the list the moved row has already left, so an index past it
  // shifts down by one.
  const shift = target > from ? -1 : 0;
  return moveRowTo(rows, from, target + shift + (placement === "after" ? 1 : 0));
}

/** What a break (or any other block) says, once its blank cells are thrown away. */
export interface BlockLine {
  /** When it starts, if that column was published. */
  time: string;
  /** What it is called — «Перерыв», «Награждение». */
  title: string;
  /** Everything else the row carries: its length, a comment, a hand-filled column. */
  extras: string[];
}

/**
 * Read a non-performance row as one line of text rather than as a row of cells.
 *
 * A break has no participant, no age category and no number, so published alongside the
 * acts it is a dozen blank cells with «Перерыв» somewhere inside them — and on a table
 * cut for the sound desk that somewhere can be two screens to the right. Everything the
 * row actually says fits in a line, and a line is what the screen draws: the clock, the
 * name, and whatever else was filled in, all at the left edge where nobody has to scroll
 * for it.
 *
 * The title falls back to the first cell that says anything, so a block stays legible on
 * an edition published without the «Номер» column at all.
 */
export function blockLine(row: PublicProgramRow, columns: readonly string[]): BlockLine {
  const at = (key: string) => columns.indexOf(key);
  const cellAt = (index: number) => (index >= 0 ? (row.cells[index] ?? "").trim() : "");
  const timeAt = at("TIME");
  let titleAt = at("TITLE");
  if (cellAt(titleAt) === "") {
    titleAt = row.cells.findIndex((cell, index) => index !== timeAt && cell.trim().length > 0);
  }
  const extras = row.cells
    .map((cell, index) => (index === timeAt || index === titleAt ? "" : cell.trim()))
    .filter((cell) => cell.length > 0);
  return { time: cellAt(timeAt), title: cellAt(titleAt), extras };
}
