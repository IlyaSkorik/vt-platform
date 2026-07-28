import { describe, expect, it } from "vitest";

import { formatClock, formatDuration, formatSpan } from "./duration";

describe("formatDuration", () => {
  it("renders minutes and zero-padded seconds", () => {
    expect(formatDuration(215)).toBe("3:35");
    expect(formatDuration(60)).toBe("1:00");
    expect(formatDuration(9)).toBe("0:09");
  });

  it("never renders a negative slot", () => {
    expect(formatDuration(-5)).toBe("0:00");
  });
});

describe("formatSpan", () => {
  it("renders minutes alone under an hour", () => {
    expect(formatSpan(1500)).toBe("25 мин");
  });

  it("renders hours and minutes", () => {
    expect(formatSpan(7500)).toBe("2 ч 5 мин");
  });

  it("drops the minutes on a whole hour", () => {
    expect(formatSpan(3600)).toBe("1 ч");
  });
});

describe("formatClock", () => {
  it("renders an untimed programme as a dash", () => {
    expect(formatClock(null)).toBe("—");
  });

  it("renders unparseable input as a dash rather than Invalid Date", () => {
    expect(formatClock("не дата")).toBe("—");
  });

  it("renders an instant as hours and minutes", () => {
    // Formatted in the runner's timezone, so assert the shape rather than the value.
    expect(formatClock("2026-08-01T10:04:00Z")).toMatch(/^\d{2}:\d{2}$/);
  });
});
