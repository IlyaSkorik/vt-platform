import { describe, expect, it } from "vitest";
import {
  APPLICATION_STATUS,
  COMPETITION_STATUS,
  formatMoney,
  formatNumber,
  formatPercent,
  formatRelativeTime,
} from "./format";

describe("dashboard formatters", () => {
  it("groups large integers in ru-RU (non-breaking space separators)", () => {
    // ru-RU uses U+00A0 as the grouping separator, not a regular space.
    expect(formatNumber(1284)).toBe("1 284");
  });

  it("formats minor-unit amounts as localized currency", () => {
    // 4 820 000 minor units → 48 200,00 in major units.
    const formatted = formatMoney(4_820_000, "BYN");
    expect(formatted).toContain("48 200");
  });

  it("shows an explicit sign on percentages", () => {
    expect(formatPercent(12.5)).toBe("+12,5 %");
    expect(formatPercent(-3.2)).toBe("-3,2 %");
    expect(formatPercent(0)).toBe("0 %");
  });

  it("renders relative time against a fixed reference point", () => {
    const now = new Date("2026-07-08T12:00:00Z");
    const twoHoursAgo = new Date("2026-07-08T10:00:00Z").toISOString();
    expect(formatRelativeTime(twoHoursAgo, now)).toContain("2");
  });

  it("maps every competition status to a label and badge variant", () => {
    expect(COMPETITION_STATUS.judging.label).toBe("Судейство");
    expect(COMPETITION_STATUS.judging.variant).toBe("warning");
    expect(COMPETITION_STATUS.cancelled.variant).toBe("danger");
  });

  it("maps every application status to a label and badge variant", () => {
    expect(APPLICATION_STATUS.accepted.variant).toBe("success");
    expect(APPLICATION_STATUS.rejected.variant).toBe("danger");
  });
});
