import { describe, expect, it } from "vitest";
import { makeFestival } from "./fixtures";
import {
  daysUntil,
  formatAgeRange,
  formatDeadline,
  formatPeriod,
  formatPrice,
  isClosingSoon,
  parseApiDate,
} from "./format";

const NOW = new Date("2026-07-15T12:00:00Z");

describe("parseApiDate", () => {
  it("parses date-only strings in local time (no day shift)", () => {
    const date = parseApiDate("2026-07-12");
    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(6);
    expect(date?.getDate()).toBe(12);
  });

  it("returns null for empty or invalid input", () => {
    expect(parseApiDate(null)).toBeNull();
    expect(parseApiDate("not-a-date")).toBeNull();
  });
});

describe("formatPeriod", () => {
  it("collapses a same-day range to one date", () => {
    expect(formatPeriod("2026-08-01", "2026-08-01")).toBe(formatPeriod("2026-08-01", null));
  });

  it("renders a range", () => {
    expect(formatPeriod("2026-08-01", "2026-08-03")).toContain("–");
  });

  it("returns null when both bounds are missing", () => {
    expect(formatPeriod(null, null)).toBeNull();
  });
});

describe("formatPrice", () => {
  it("prefixes 'от' when multiple prices exist", () => {
    const festival = makeFestival({
      pricing: { amountFrom: "30", currency: "BYN", multiple: true },
    });
    expect(formatPrice(festival)).toBe("от 30 BYN");
  });

  it("omits the prefix for a single price", () => {
    const festival = makeFestival({
      pricing: { amountFrom: "50", currency: "BYN", multiple: false },
    });
    expect(formatPrice(festival)).toBe("50 BYN");
  });

  it("returns null when no price is configured", () => {
    const festival = makeFestival({
      pricing: { amountFrom: null, currency: null, multiple: false },
    });
    expect(formatPrice(festival)).toBeNull();
  });
});

describe("daysUntil", () => {
  it("counts whole days ahead", () => {
    expect(daysUntil("2026-07-20", NOW)).toBe(5);
  });

  it("is negative for past dates", () => {
    expect(daysUntil("2026-07-10", NOW)).toBeLessThan(0);
  });
});

describe("isClosingSoon", () => {
  it("is true for an open registration closing within the window", () => {
    const festival = makeFestival({ status: "REGISTRATION_OPEN", registrationEnd: "2026-07-18" });
    expect(isClosingSoon(festival, NOW)).toBe(true);
  });

  it("is false when the window is far out", () => {
    const festival = makeFestival({ status: "REGISTRATION_OPEN", registrationEnd: "2026-09-01" });
    expect(isClosingSoon(festival, NOW)).toBe(false);
  });

  it("is false when registration is not open", () => {
    const festival = makeFestival({ status: "COMING_SOON", registrationEnd: "2026-07-18" });
    expect(isClosingSoon(festival, NOW)).toBe(false);
  });

  it("uses the explicit application deadline when present", () => {
    const festival = makeFestival({
      status: "REGISTRATION_OPEN",
      registrationEnd: "2026-09-01",
      applicationDeadline: "2026-07-17T23:59:00Z",
    });
    expect(isClosingSoon(festival, NOW)).toBe(true);
    expect(formatDeadline(festival)).not.toBeNull();
  });
});

describe("formatAgeRange", () => {
  it("renders the span the projection sends", () => {
    expect(formatAgeRange(makeFestival({ ageMin: 12, ageMax: 18 }))).toBe("12–18 лет");
  });

  it("agrees the noun with the bound it follows", () => {
    // «лет» would be wrong on 21 and right on 18 — the trailing number decides.
    expect(formatAgeRange(makeFestival({ ageMin: 12, ageMax: 21 }))).toBe("12–21 год");
    expect(formatAgeRange(makeFestival({ ageMin: 12, ageMax: 22 }))).toBe("12–22 года");
  });

  it("collapses a single-year band to one number", () => {
    expect(formatAgeRange(makeFestival({ ageMin: 7, ageMax: 7 }))).toBe("7 лет");
  });

  it("still reads a half-open band", () => {
    expect(formatAgeRange(makeFestival({ ageMin: 7, ageMax: null }))).toBe("от 7 лет");
    expect(formatAgeRange(makeFestival({ ageMin: null, ageMax: 18 }))).toBe("до 18 лет");
  });

  it("is null when the festival declares no age categories", () => {
    expect(formatAgeRange(makeFestival({ ageMin: null, ageMax: null }))).toBeNull();
  });
});
