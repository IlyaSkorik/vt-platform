import { describe, expect, it } from "vitest";

import { formatClock, formatDuration } from "@/shared/lib";

import {
  type ArrangementSettings,
  arrangeInput,
  DEFAULT_ARRANGEMENT,
  groupRuns,
  itemCell,
  itemNumber,
  moveBlock,
  moveItem,
  moveItemNextTo,
  type ProgramItem,
} from "./model";

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
    participants: ["Иванов Иван"],
    participantCount: 1,
    teachers: ["Петрова Мария", "Сидорова Анна"],
    contacts: [],
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

  it("names every performer of an entry, not just the first", () => {
    // A duet is two performer rows on one entry, and a programme that prints one of the
    // two names tells the hall the wrong thing about who is on stage.
    const duet = anItem({ participants: ["Иванова Анна", "Петров Пётр"], participantCount: 2 });
    expect(itemCell(duet, "PARTICIPANT", FORMAT)).toBe("Иванова Анна, Петров Пётр");
  });

  it("leaves a block's absent columns blank rather than filling in a placeholder", () => {
    const pause = anItem({
      kind: "BREAK",
      title: "Перерыв",
      submissionId: null,
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
    // And no number at all: numbering a break pushes every act after it one place along.
    expect(itemCell(pause, "POSITION", FORMAT)).toBe("");
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

/**
 * The move by number: what the organizer reaches for when an act at the bottom of the
 * programme has to go to the top while the day is running. It reads the number printed
 * in the programme, which after a freeze is not the row's index — pointing it at a row
 * instead would move a different act than the one the host just named.
 */
describe("moveItemNextTo", () => {
  /** A programme whose numbers no longer match the rows, as a published one's do not. */
  function frozen(): ProgramItem[] {
    return [
      anItem({ id: "a", number: 2, schedule: { ...anItem().schedule, position: 1 } }),
      anItem({ id: "b", number: 3, schedule: { ...anItem().schedule, position: 2 } }),
      anItem({ id: "c", number: 5, schedule: { ...anItem().schedule, position: 3 } }),
      anItem({ id: "d", number: 4, schedule: { ...anItem().schedule, position: 4 } }),
    ];
  }

  const ids = (items: ProgramItem[] | null) => items?.map((item) => item.id);

  it("puts a slot from the end in front of a number near the start", () => {
    expect(ids(moveItemNextTo(frozen(), 3, 2, "before"))).toEqual(["d", "a", "b", "c"]);
  });

  it("puts a slot straight after the number it was pointed at", () => {
    expect(ids(moveItemNextTo(frozen(), 3, 2, "after"))).toEqual(["a", "d", "b", "c"]);
  });

  it("counts from the list the moved slot has already left, moving downwards too", () => {
    // «После №4» from the top: three rows down, not two — the row it vacated shifts the rest up.
    expect(ids(moveItemNextTo(frozen(), 0, 4, "after"))).toEqual(["b", "c", "d", "a"]);
    expect(ids(moveItemNextTo(frozen(), 0, 4, "before"))).toEqual(["b", "c", "a", "d"]);
  });

  it("reads the printed number rather than the row, so the right act moves", () => {
    // №5 is the third row and №4 the fourth; a row-index reading would move the wrong one.
    expect(ids(moveItemNextTo(frozen(), 0, 5, "after"))).toEqual(["b", "c", "a", "d"]);
  });

  it("says so when nothing in the programme carries that number", () => {
    expect(moveItemNextTo(frozen(), 0, 9, "after")).toBeNull();
  });

  it("is a no-op when a slot is pointed at itself", () => {
    expect(ids(moveItemNextTo(frozen(), 2, 5, "before"))).toEqual(["a", "b", "c", "d"]);
  });

  it("does not mutate the input", () => {
    const items = frozen();
    moveItemNextTo(items, 3, 2, "before");
    expect(ids(items)).toEqual(["a", "b", "c", "d"]);
  });
});

/**
 * The number the control asks about is the one on screen: the printed one once frozen,
 * the row's own while the programme is still being assembled.
 */
describe("itemNumber", () => {
  it("prefers the participant's own number", () => {
    expect(itemNumber(anItem({ number: 12 }))).toBe(12);
  });

  it("falls back to the row while the programme has no numbers yet", () => {
    const unnumbered = anItem({
      number: 0,
      schedule: { ...anItem().schedule, position: 7 },
    });
    expect(itemNumber(unnumbered)).toBe(7);
  });

  it("answers that a service block has no number", () => {
    expect(itemNumber(anItem({ kind: "BREAK", number: 0 }))).toBeNull();
    expect(itemNumber(anItem({ kind: "AWARD", number: 4 }))).toBeNull();
  });
});

describe("arrangeInput", () => {
  function settings(overrides: Partial<ArrangementSettings> = {}): ArrangementSettings {
    return { ...DEFAULT_ARRANGEMENT, ...overrides };
  }

  it("omits the break entirely when no rule fires", () => {
    // A break the generator will never insert is not a setting, it is noise on the wire.
    const input = arrangeInput(settings({ breakRule: "NONE" }));
    expect(input.breakTitle).toBeUndefined();
    expect(input.breakDurationSeconds).toBeUndefined();
    expect(input.breakAfterItems).toBeUndefined();
  });

  it("sends only the interval the chosen rule reads", () => {
    const byCount = arrangeInput(settings({ breakRule: "EVERY_COUNT", breakAfterItems: 12 }));
    expect(byCount.breakAfterItems).toBe(12);
    expect(byCount.breakAfterSeconds).toBeUndefined();

    const byDuration = arrangeInput(
      settings({ breakRule: "EVERY_DURATION", breakAfterSeconds: 5400 }),
    );
    expect(byDuration.breakAfterSeconds).toBe(5400);
    expect(byDuration.breakAfterItems).toBeUndefined();
  });

  it("switches a service block on by naming it", () => {
    const off = arrangeInput(settings({ openingTitle: null }));
    expect(off.openingTitle).toBeUndefined();
    expect(off.openingDurationSeconds).toBeUndefined();

    const on = arrangeInput(settings({ openingTitle: "Открытие", openingDurationSeconds: 600 }));
    expect(on).toMatchObject({ openingTitle: "Открытие", openingDurationSeconds: 600 });
  });

  it("keeps the grouping order, because the order is the shape of the day", () => {
    const input = arrangeInput(settings({ grouping: ["AGE_CATEGORY", "NOMINATION"] }));
    expect(input.grouping).toEqual(["AGE_CATEGORY", "NOMINATION"]);
  });

  it("always states the repeat gap, so turning it off is an instruction too", () => {
    expect(arrangeInput(settings({ repeatGap: 0 })).repeatGap).toBe(0);
  });
});

/**
 * The move the day is actually planned with: a whole genre picked up at once.
 *
 * `to` is an insertion index into the list *as it is now*, which is what a drop between
 * two rows means — and the run has to be lifted out before it can be put back, so every
 * index past it shifts down by the run's own length. Getting that off by one sends a
 * running order nobody asked for, and the endpoint takes the whole order, so nothing
 * downstream can catch it.
 */
describe("moveBlock", () => {
  const day = () => ["a", "b", "c", "d", "e"];

  it("lifts a run from the middle to the very front", () => {
    expect(moveBlock(day(), 2, 2, 0)).toEqual(["c", "d", "a", "b", "e"]);
  });

  it("lifts a run from the front to the very end", () => {
    expect(moveBlock(day(), 0, 2, 5)).toEqual(["c", "d", "e", "a", "b"]);
  });

  it("counts from the list the run has already left, moving downwards", () => {
    // Dropped in front of "e", which is index 4 now and index 2 once a,b are gone.
    expect(moveBlock(day(), 0, 2, 4)).toEqual(["c", "d", "a", "b", "e"]);
  });

  it("is a no-op when a run is dropped on itself or on either of its own edges", () => {
    expect(moveBlock(day(), 1, 2, 1)).toEqual(day());
    expect(moveBlock(day(), 1, 2, 2)).toEqual(day());
    expect(moveBlock(day(), 1, 2, 3)).toEqual(day());
  });

  it("ignores a run or a destination that is not in the list", () => {
    expect(moveBlock(day(), 4, 3, 0)).toEqual(day());
    expect(moveBlock(day(), 0, 2, 9)).toEqual(day());
    expect(moveBlock(day(), -1, 2, 0)).toEqual(day());
  });

  it("does not mutate the list it was given", () => {
    const original = day();
    moveBlock(original, 0, 2, 5);
    expect(original).toEqual(["a", "b", "c", "d", "e"]);
  });
});

/**
 * Grouping is a *reading* of the running order, never a rearrangement of it — which is
 * what makes a group safe to drag: it is a contiguous slice of the day, so moving it
 * leaves everything outside it exactly where the organizer put it.
 */
describe("groupRuns", () => {
  const shape = (items: ProgramItem[]) =>
    groupRuns(items, "DISCIPLINE").map((group) => [group.label, group.start, group.items.length]);

  it("joins consecutive slots that share the value", () => {
    expect(
      shape([
        anItem({ id: "a", discipline: "Эстрадный вокал" }),
        anItem({ id: "b", discipline: "Эстрадный вокал" }),
        anItem({ id: "c", discipline: "Народный вокал" }),
      ]),
    ).toEqual([
      ["Эстрадный вокал", 0, 2],
      ["Народный вокал", 2, 1],
    ]);
  });

  it("keeps one value that appears twice as two groups", () => {
    // The order on screen is the order of the day; pretending the two halves are one
    // group would make dragging it reorder rows the organizer never touched.
    expect(
      shape([
        anItem({ id: "a", discipline: "Эстрадный вокал" }),
        anItem({ id: "b", discipline: "Народный вокал" }),
        anItem({ id: "c", discipline: "Эстрадный вокал" }),
      ]),
    ).toEqual([
      ["Эстрадный вокал", 0, 1],
      ["Народный вокал", 1, 1],
      ["Эстрадный вокал", 2, 1],
    ]);
  });

  it("leaves a break standing alone, named by its own title", () => {
    // Otherwise dragging вокал somewhere would take lunch along with it.
    const groups = groupRuns(
      [
        anItem({ id: "a", discipline: "Эстрадный вокал" }),
        anItem({ id: "pause", kind: "BREAK", title: "Обед", discipline: null }),
        anItem({ id: "b", discipline: "Эстрадный вокал" }),
      ],
      "DISCIPLINE",
    );
    expect(groups.map((group) => [group.label, group.standalone])).toEqual([
      ["Эстрадный вокал", false],
      ["Обед", true],
      ["Эстрадный вокал", false],
    ]);
  });

  it("says plainly when a slot has nothing in that column", () => {
    expect(shape([anItem({ id: "a", discipline: null })])).toEqual([["—", 0, 1]]);
  });
});
