import { describe, expect, it } from "vitest";
import { formatClock } from "./duration";
import { festivalInputToIso, isoToFestivalInput } from "./festival-time";

/**
 * The pact that keeps a programme reading the same time everywhere.
 *
 * Europe/Minsk is UTC+3 all year, so "10:00 в зале" is "07:00Z" in storage — and that
 * three-hour gap is exactly what used to separate the constructor from the link it
 * generated. Every case here is the same minute said two ways.
 */
describe("festival time", () => {
  it("reads a typed wall clock as the hall's time, not the laptop's", () => {
    expect(festivalInputToIso("2026-08-01T10:00")).toBe("2026-08-01T07:00:00.000Z");
  });

  it("puts a stored instant back into the picker as the hall's time", () => {
    expect(isoToFestivalInput("2026-08-01T07:00:00Z")).toBe("2026-08-01T10:00");
  });

  it("round-trips a wall clock unchanged", () => {
    const typed = "2026-12-31T23:30";
    expect(isoToFestivalInput(festivalInputToIso(typed))).toBe(typed);
  });

  it("renders a cell in the same zone the server renders it in", () => {
    expect(formatClock("2026-08-01T07:00:00Z")).toBe("10:00");
  });

  it("says nothing about a programme that has no start time", () => {
    expect(festivalInputToIso("")).toBeNull();
    expect(isoToFestivalInput(null)).toBe("");
    expect(isoToFestivalInput("не дата")).toBe("");
  });
});
