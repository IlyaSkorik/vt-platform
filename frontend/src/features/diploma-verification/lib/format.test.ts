import { describe, expect, it } from "vitest";
import { formatCheckedAt, formatCompetitionDate } from "./format";

describe("formatCompetitionDate", () => {
  it("reads a snapshot date as a document does", () => {
    expect(formatCompetitionDate("12.04.2026")).toBe("12 апреля 2026");
  });

  it("drops the ru-RU era marker", () => {
    expect(formatCompetitionDate("01.01.2026")).not.toMatch(/г\./);
  });

  it("returns an unrecognised value verbatim", () => {
    // A snapshot is immutable and may predate the current format; showing what was
    // frozen beats showing nothing.
    expect(formatCompetitionDate("весна 2026")).toBe("весна 2026");
    expect(formatCompetitionDate("2026")).toBe("2026");
  });

  it("rejects an impossible date rather than rolling it over", () => {
    // Naive Date arithmetic would turn 31.02 into 3 March — a date the document
    // never carried.
    expect(formatCompetitionDate("31.02.2026")).toBe("31.02.2026");
  });

  it("has nothing to show for an absent date", () => {
    expect(formatCompetitionDate(null)).toBeNull();
    expect(formatCompetitionDate("  ")).toBeNull();
  });
});

describe("formatCheckedAt", () => {
  it("stamps the moment of the check", () => {
    expect(formatCheckedAt(new Date(2026, 6, 26, 18, 42))).toBe("26.07.2026 18:42");
  });

  it("pads every component to a fixed width", () => {
    expect(formatCheckedAt(new Date(2026, 0, 5, 9, 7))).toBe("05.01.2026 09:07");
  });
});
