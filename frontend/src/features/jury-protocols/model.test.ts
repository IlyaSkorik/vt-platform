import { describe, expect, it } from "vitest";

import {
  canPublish,
  moveRow,
  type Protocol,
  type ProtocolRow,
  rowCell,
  undecidedCount,
} from "./model";

function aRow(overrides: Partial<ProtocolRow> = {}): ProtocolRow {
  return {
    id: "row-1",
    number: 3,
    submissionId: "sub-1",
    title: "Катюша",
    award: "LAUREATE_II",
    awardLabel: "Лауреат II степени",
    participants: ["Иванов Иван"],
    teachers: ["Петрова Мария", "Сидорова Анна"],
    nomination: "Вокал",
    discipline: "Эстрадный вокал",
    ageCategory: "10-12 лет",
    participantGroup: "Соло",
    participationFormat: "Очно",
    organization: "Школа №1",
    missingPerformance: false,
    ...overrides,
  };
}

function aProtocol(rows: ProtocolRow[]): Protocol {
  return {
    id: "protocol-1",
    competitionId: "competition-1",
    nominationId: "nomination-1",
    nomination: "Вокал",
    competitionTitle: "Взлёт талантов",
    name: "Вокал",
    status: "DRAFT",
    rows,
    availableColumns: [],
    publicColumns: [],
    awardOptions: [],
    revision: 0,
    slug: null,
    path: null,
    publishedAt: null,
    hasUnpublishedChanges: false,
    seededFromProgramId: null,
    createdAt: "2026-08-01T18:00:00Z",
    updatedAt: "2026-08-01T18:00:00Z",
    version: 1,
  };
}

describe("rowCell", () => {
  it("renders the award as the wording the backend sent, never a local mapping", () => {
    // The whole point of carrying `awardLabel`: the same words appear on the diploma and in
    // the letter, and a second copy of that vocabulary here is how the three come to disagree.
    expect(rowCell(aRow(), "AWARD")).toBe("Лауреат II степени");
  });

  it("renders an undecided row's result as blank, not as a placeholder", () => {
    expect(rowCell(aRow({ award: null, awardLabel: null }), "AWARD")).toBe("");
  });

  it("shows the number the act performed under", () => {
    expect(rowCell(aRow({ number: 7 }), "POSITION")).toBe("7");
  });

  it("joins several teachers into one cell", () => {
    expect(rowCell(aRow(), "TEACHERS")).toBe("Петрова Мария, Сидорова Анна");
  });

  it("names every performer of an entry, not just the first", () => {
    // A duet wins its award together, and naming one of the two is wrong about who it
    // went to — the same join the backend applies to the published protocol.
    const duet = aRow({ participants: ["Иванова Анна", "Петров Пётр"] });
    expect(rowCell(duet, "PARTICIPANT")).toBe("Иванова Анна, Петров Пётр");
  });

  it("renders a missing optional value as blank rather than as text", () => {
    expect(rowCell(aRow({ organization: null }), "ORGANIZATION")).toBe("");
  });
});

describe("undecidedCount", () => {
  it("counts the rows the jury still has to decide", () => {
    const protocol = aProtocol([
      aRow({ id: "a" }),
      aRow({ id: "b", award: null, awardLabel: null }),
      aRow({ id: "c", award: null, awardLabel: null }),
    ]);
    expect(undecidedCount(protocol)).toBe(2);
  });

  it("is zero for a finished protocol", () => {
    expect(undecidedCount(aProtocol([aRow()]))).toBe(0);
  });
});

describe("canPublish", () => {
  it("refuses a protocol where nothing has been decided", () => {
    // Publishing then would announce results nobody decided and issue blank diplomas.
    expect(canPublish(aProtocol([aRow({ award: null, awardLabel: null })]))).toBe(false);
  });

  it("refuses an empty protocol", () => {
    expect(canPublish(aProtocol([]))).toBe(false);
  });

  it("allows a protocol with blanks in it", () => {
    // An act that did not appear is a blank line, not a reason to hold a nomination's results.
    const protocol = aProtocol([
      aRow({ id: "a" }),
      aRow({ id: "b", award: null, awardLabel: null }),
    ]);
    expect(canPublish(protocol)).toBe(true);
  });
});

describe("moveRow", () => {
  it("returns the complete new order, since that is what the endpoint takes", () => {
    expect(moveRow(["a", "b", "c"], 2, 0)).toEqual(["c", "a", "b"]);
  });

  it("leaves the order untouched when the move goes nowhere", () => {
    expect(moveRow(["a", "b", "c"], 1, 1)).toEqual(["a", "b", "c"]);
  });

  it("leaves the order untouched when the move runs off either end", () => {
    expect(moveRow(["a", "b", "c"], 0, -1)).toEqual(["a", "b", "c"]);
    expect(moveRow(["a", "b", "c"], 2, 3)).toEqual(["a", "b", "c"]);
  });
});
