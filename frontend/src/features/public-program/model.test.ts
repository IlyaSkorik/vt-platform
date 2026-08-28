import { describe, expect, it } from "vitest";

import type { PublicProgramRow } from "./api";
import { moveRowNextTo, moveRowTo, rowNumber } from "./model";

const COLUMNS = ["POSITION", "TIME", "TITLE"];

function aRow(number: string, id: string | null = `item-${number}`): PublicProgramRow {
  return { kind: "PERFORMANCE", cells: [number, "10:00", "Катюша"], progress: "PENDING", id };
}

/** A published programme, whose numbers stayed with their participants: 4, 9, 7. */
function published(): PublicProgramRow[] {
  return [aRow("4"), aRow("9"), aRow("7")];
}

/**
 * Which number the form means. Read it wrong and the host moves a different act than the
 * one just announced — the reorder sends the complete order, so nothing downstream can
 * catch it.
 */
describe("rowNumber", () => {
  it("reads the number the host sees in the «№» column", () => {
    expect(rowNumber(aRow("7"), 0, COLUMNS)).toBe(7);
  });

  it("counts rows when that column was not published", () => {
    expect(rowNumber(aRow("7"), 2, ["TIME", "TITLE"])).toBe(3);
  });

  it("counts rows for a slot whose cell holds no number at all", () => {
    expect(rowNumber(aRow("—"), 1, COLUMNS)).toBe(2);
  });
});

describe("moveRowNextTo", () => {
  it("takes a row from the end to the front of the order", () => {
    expect(moveRowNextTo(published(), COLUMNS, 2, 4, "before")).toEqual([
      "item-7",
      "item-4",
      "item-9",
    ]);
  });

  it("counts from the list the moved row has already left, moving downwards", () => {
    expect(moveRowNextTo(published(), COLUMNS, 0, 7, "after")).toEqual([
      "item-9",
      "item-7",
      "item-4",
    ]);
  });

  it("is a no-op when a row is pointed at itself", () => {
    expect(moveRowNextTo(published(), COLUMNS, 1, 9, "after")).toEqual([
      "item-4",
      "item-9",
      "item-7",
    ]);
  });

  it("says so when the programme carries no such number", () => {
    expect(moveRowNextTo(published(), COLUMNS, 0, 5, "after")).toBeNull();
  });

  it("refuses an edition whose rows carry no ids, rather than sending blanks", () => {
    // Only the host's edition can address its rows; any other has nothing to reorder with.
    const anonymous = [aRow("4", null), aRow("9", null)];
    expect(moveRowNextTo(anonymous, COLUMNS, 1, 4, "before")).toBeNull();
    expect(moveRowTo(anonymous, 1, 0)).toBeNull();
  });

  it("ignores an out-of-range destination instead of corrupting the order", () => {
    expect(moveRowTo(published(), 0, 5)).toBeNull();
    expect(moveRowTo(published(), -1, 0)).toBeNull();
  });

  it("does not mutate the rows it was given", () => {
    const rows = published();
    moveRowNextTo(rows, COLUMNS, 2, 4, "before");
    expect(rows.map((row) => row.id)).toEqual(["item-4", "item-9", "item-7"]);
  });
});
