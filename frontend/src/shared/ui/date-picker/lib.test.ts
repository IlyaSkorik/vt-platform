import { describe, expect, it } from "vitest";

import {
  formatDateLabel,
  formatDateValue,
  joinDateTime,
  parseDateValue,
  splitDateTime,
} from "./lib";

describe("parseDateValue", () => {
  it("reads a wire date as the local day it names", () => {
    // The whole reason this is hand-rolled: `new Date("2015-04-01")` is midnight
    // *UTC*, which in any zone behind UTC is the 31st of March. That is how a
    // birth date silently loses a day, and it only shows up for some users.
    const parsed = parseDateValue("2015-04-01");

    expect(parsed?.getFullYear()).toBe(2015);
    expect(parsed?.getMonth()).toBe(3);
    expect(parsed?.getDate()).toBe(1);
  });

  it("refuses a day that does not exist", () => {
    // JavaScript would roll this into the 3rd of March rather than refuse it.
    expect(parseDateValue("2015-02-31")).toBeUndefined();
  });

  it("refuses anything that is not a wire date", () => {
    for (const value of [
      "",
      "   ",
      "01.04.2015",
      "2015-4-1",
      "2015-04-01T10:00",
      null,
      undefined,
    ]) {
      expect(parseDateValue(value)).toBeUndefined();
    }
  });
});

describe("formatDateValue", () => {
  it("round-trips through parse without shifting the day", () => {
    expect(formatDateValue(parseDateValue("2015-04-01") as Date)).toBe("2015-04-01");
  });

  it("pads single-digit months and days", () => {
    expect(formatDateValue(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("formatDateLabel", () => {
  it("shows the date the way it is read aloud", () => {
    expect(formatDateLabel("2015-04-01")).toContain("2015");
    expect(formatDateLabel("2015-04-01")).toContain("апреля");
  });

  it("has nothing to show for an empty value", () => {
    expect(formatDateLabel("")).toBeNull();
    expect(formatDateLabel(null)).toBeNull();
  });
});

describe("splitDateTime", () => {
  it("splits the datetime-local shape", () => {
    expect(splitDateTime("2026-05-20T18:30")).toEqual({ date: "2026-05-20", time: "18:30" });
  });

  it("drops seconds, which some browsers appended and nothing here wants", () => {
    expect(splitDateTime("2026-05-20T18:30:45")).toEqual({ date: "2026-05-20", time: "18:30" });
  });

  it("copes with a half-filled or absent value", () => {
    expect(splitDateTime("2026-05-20")).toEqual({ date: "2026-05-20", time: "" });
    expect(splitDateTime("")).toEqual({ date: "", time: "" });
    expect(splitDateTime(null)).toEqual({ date: "", time: "" });
  });
});

describe("joinDateTime", () => {
  it("puts the two halves back together", () => {
    expect(joinDateTime("2026-05-20", "18:30")).toBe("2026-05-20T18:30");
  });

  it("keeps a date whose time is not filled in yet, at midnight", () => {
    // "the 20th" is a complete enough answer to save while the hour is still
    // being worked out; throwing it away would lose what the user just picked.
    expect(joinDateTime("2026-05-20", "")).toBe("2026-05-20T00:00");
  });

  it("is empty when there is no date, whatever the time says", () => {
    // A time with no day names no instant at all.
    expect(joinDateTime("", "18:30")).toBe("");
  });
});
