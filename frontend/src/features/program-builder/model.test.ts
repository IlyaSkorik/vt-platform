import { describe, expect, it } from "vitest";

import { formatClock, formatDuration } from "@/shared/lib";

import { itemCell, moveItem, type ProgramItem } from "./model";

const FORMAT = { clock: formatClock, duration: formatDuration };

function anItem(overrides: Partial<ProgramItem> = {}): ProgramItem {
  return {
    id: "item-1",
    kind: "PERFORMANCE",
    title: "Катюша",
    number: 3,
    customValues: {},
    progress: "PENDING",
    durationSeconds: 200,
    schedule: {
      position: 3,
      offsetSeconds: 400,
      slotSeconds: 230,
      startsAt: null,
      endsAt: null,
    },
    submissionId: "sub-1",
    leadParticipant: "Иванов Иван",
    participants: ["Иванов Иван"],
    teachers: ["Петрова Мария", "Сидорова Анна"],
    nomination: "Вокал",
    discipline: "Эстрадный вокал",
    ageCategory: "10-12 лет",
    participantGroup: "Соло",
    participationFormat: "Очно",
    organization: "Школа №1",
    comment: "Выход с точки 3",
    missingPerformance: false,
    ...overrides,
  };
}

/**
 * `itemCell` mirrors the backend's cell renderer. If the two disagree, the organizer's
 * table and a published link show different text for the same data.
 */
describe("itemCell", () => {
  it("renders every column of a performance row", () => {
    const item = anItem();
    expect(itemCell(item, "POSITION", FORMAT)).toBe("3");
    expect(itemCell(item, "PARTICIPANT", FORMAT)).toBe("Иванов Иван");
    expect(itemCell(item, "TITLE", FORMAT)).toBe("Катюша");
    expect(itemCell(item, "DURATION", FORMAT)).toBe("3:20");
    expect(itemCell(item, "NOMINATION", FORMAT)).toBe("Вокал");
    expect(itemCell(item, "DISCIPLINE", FORMAT)).toBe("Эстрадный вокал");
    expect(itemCell(item, "PARTICIPANT_GROUP", FORMAT)).toBe("Соло");
    expect(itemCell(item, "AGE_CATEGORY", FORMAT)).toBe("10-12 лет");
    expect(itemCell(item, "PARTICIPATION_FORMAT", FORMAT)).toBe("Очно");
    expect(itemCell(item, "ORGANIZATION", FORMAT)).toBe("Школа №1");
    expect(itemCell(item, "COMMENT", FORMAT)).toBe("Выход с точки 3");
  });

  it("joins several teachers into one cell", () => {
    expect(itemCell(anItem(), "TEACHERS", FORMAT)).toBe("Петрова Мария, Сидорова Анна");
  });

  it("leaves a block's absent columns blank rather than filling in a placeholder", () => {
    const pause = anItem({
      kind: "BREAK",
      title: "Перерыв",
      submissionId: null,
      leadParticipant: null,
      participants: [],
      teachers: [],
      nomination: null,
      discipline: null,
      ageCategory: null,
      participantGroup: null,
      participationFormat: null,
      organization: null,
      comment: null,
    });
    expect(itemCell(pause, "PARTICIPANT", FORMAT)).toBe("");
    expect(itemCell(pause, "AGE_CATEGORY", FORMAT)).toBe("");
    expect(itemCell(pause, "TEACHERS", FORMAT)).toBe("");
    // A block still has a title and a length — that is what makes it schedulable.
    expect(itemCell(pause, "TITLE", FORMAT)).toBe("Перерыв");
    expect(itemCell(pause, "DURATION", FORMAT)).toBe("3:20");
  });

  it("renders an untimed programme's time cell as a dash", () => {
    expect(itemCell(anItem(), "TIME", FORMAT)).toBe("—");
  });

  it("puts the participant's permanent number in the № cell, not the row index", () => {
    // Row 1 of a rearranged programme can legitimately be номер 3.
    const moved = anItem({
      number: 3,
      schedule: { position: 1, offsetSeconds: 0, slotSeconds: 200, startsAt: null, endsAt: null },
    });
    expect(itemCell(moved, "POSITION", FORMAT)).toBe("3");
  });

  it("falls back to the row index for a slot that has no number yet", () => {
    const legacy = anItem({
      number: 0,
      schedule: { position: 7, offsetSeconds: 0, slotSeconds: 200, startsAt: null, endsAt: null },
    });
    expect(itemCell(legacy, "POSITION", FORMAT)).toBe("7");
  });
});

/**
 * `moveItem` is the only place the running order is rearranged client-side: the reorder
 * endpoint takes the complete new order, so a wrong result here would silently send a
 * different programme than the organizer sees.
 */
describe("moveItem", () => {
  it("moves an item down one place", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
  });

  it("moves an item up one place", () => {
    expect(moveItem(["a", "b", "c"], 2, 1)).toEqual(["a", "c", "b"]);
  });

  it("keeps every item, so a reorder can never drop a slot", () => {
    const result = moveItem(["a", "b", "c", "d"], 3, 0);
    expect(result).toEqual(["d", "a", "b", "c"]);
    expect(result).toHaveLength(4);
  });

  it("returns an unchanged copy when the move is a no-op", () => {
    const items = ["a", "b"];
    expect(moveItem(items, 1, 1)).toEqual(items);
  });

  it("ignores out-of-range indices instead of corrupting the order", () => {
    expect(moveItem(["a", "b"], 0, 5)).toEqual(["a", "b"]);
    expect(moveItem(["a", "b"], -1, 0)).toEqual(["a", "b"]);
  });

  it("does not mutate the input", () => {
    const items = ["a", "b", "c"];
    moveItem(items, 0, 2);
    expect(items).toEqual(["a", "b", "c"]);
  });
});
