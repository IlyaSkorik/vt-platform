import { describe, expect, it } from "vitest";

import { digitsOf, maskTime, normaliseTime, partAtCaret, stepTime } from "./lib";

describe("maskTime", () => {
  it("lays the colon in as digits arrive", () => {
    expect(maskTime("1")).toBe("1");
    expect(maskTime("11")).toBe("11");
    expect(maskTime("114")).toBe("11:4");
    expect(maskTime("1147")).toBe("11:47");
  });

  it("closes a one-digit hour early when nothing else could follow", () => {
    // There is no hour starting with 9, so the 9 can only be the whole hour —
    // the colon lands now and the next keystroke is already a minute.
    expect(maskTime("9")).toBe("09:");
    expect(maskTime("945")).toBe("09:45");
  });

  it("does the same for a two-digit run that cannot be an hour", () => {
    expect(maskTime("45")).toBe("04:5");
  });

  it("ignores everything that is not a digit, so a pasted time still works", () => {
    expect(maskTime("11:47")).toBe("11:47");
    expect(maskTime("11ч47м")).toBe("11:47");
  });

  it("stops at four digits", () => {
    expect(maskTime("114799")).toBe("11:47");
  });

  it("has nothing to lay out for an empty field", () => {
    expect(maskTime("")).toBe("");
    expect(maskTime("абв")).toBe("");
  });
});

describe("normaliseTime", () => {
  it("pads what a keyboard produces", () => {
    expect(normaliseTime("9:05")).toBe("09:05");
    expect(normaliseTime("9:5")).toBe("09:05");
  });

  it("refuses what is not yet, or never was, a time", () => {
    for (const value of ["", "11", "11:", "25:00", "12:60", "abc"]) {
      expect(normaliseTime(value)).toBe("");
    }
  });
});

describe("stepTime", () => {
  it("steps the half the caret is in", () => {
    expect(stepTime("11:47", "hours", 1)).toBe("12:47");
    expect(stepTime("11:47", "minutes", -1)).toBe("11:46");
  });

  it("wraps instead of stopping", () => {
    // 23:00 plus an hour is midnight everywhere except in software that gave up.
    expect(stepTime("23:00", "hours", 1)).toBe("00:00");
    expect(stepTime("00:00", "hours", -1)).toBe("23:00");
    expect(stepTime("10:59", "minutes", 1)).toBe("10:00");
    expect(stepTime("10:00", "minutes", -1)).toBe("10:59");
  });

  it("starts from midnight when the field is empty", () => {
    // So the first press of Up produces something usable rather than nothing.
    expect(stepTime("", "hours", 1)).toBe("01:00");
  });
});

describe("partAtCaret", () => {
  it("reads the caret position as one half or the other", () => {
    expect(partAtCaret(0)).toBe("hours");
    expect(partAtCaret(2)).toBe("hours");
    expect(partAtCaret(3)).toBe("minutes");
    expect(partAtCaret(5)).toBe("minutes");
    expect(partAtCaret(null)).toBe("hours");
  });
});

describe("digitsOf", () => {
  it("keeps at most four digits and nothing else", () => {
    expect(digitsOf("11:47")).toBe("1147");
    expect(digitsOf("")).toBe("");
  });
});
