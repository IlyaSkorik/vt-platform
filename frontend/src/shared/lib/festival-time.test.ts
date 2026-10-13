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

  /**
   * The one correction this module makes to what the formatter hands back is that an
   * hour of `24` means midnight. Applied to every part instead of only the hour, it
   * read the 24th of the month as the 0th — so a programme held on the 24th came back
   * as `2026-10-00`, the field could not parse it, and the date simply disappeared.
   * Set it again, same thing. It was never about future dates, nor about saving: the
   * server had it right the whole time, and only a `24` anywhere in the date was lost.
   */
  describe("the 24th is a day of the month, not a midnight", () => {
    it.each([
      ["2026-10-24T07:00:00Z", "2026-10-24T10:00"],
      ["2026-02-24T21:00:00Z", "2026-02-25T00:00"],
      ["2026-08-01T07:24:00Z", "2026-08-01T10:24"],
      ["2026-12-24T21:24:00Z", "2026-12-25T00:24"],
    ])("keeps every 24 in %s", (iso, expected) => {
      expect(isoToFestivalInput(iso)).toBe(expected);
    });

    it("still reads a midnight hour as the start of its day", () => {
      // Which is what the correction was for: the day must not roll forward with it.
      expect(isoToFestivalInput("2026-10-23T21:00:00Z")).toBe("2026-10-24T00:00");
    });

    it("round-trips every day of a month", () => {
      for (let day = 1; day <= 31; day += 1) {
        const typed = `2026-10-${String(day).padStart(2, "0")}T10:00`;
        expect(isoToFestivalInput(festivalInputToIso(typed))).toBe(typed);
      }
    });

    it("round-trips every minute of an hour", () => {
      for (let minute = 0; minute < 60; minute += 1) {
        const typed = `2026-10-24T10:${String(minute).padStart(2, "0")}`;
        expect(isoToFestivalInput(festivalInputToIso(typed))).toBe(typed);
      }
    });
  });
});
