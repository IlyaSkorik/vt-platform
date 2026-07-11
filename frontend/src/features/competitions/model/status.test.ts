import { describe, expect, it } from "vitest";
import { competitionStatusLabel, matchesStatusFilter } from "../model/status";

describe("competition status helpers", () => {
  it("maps known statuses to labels", () => {
    expect(competitionStatusLabel("DRAFT")).toBe("Draft");
    expect(competitionStatusLabel("REGISTRATION_OPEN")).toBe("Registration Open");
  });

  it("treats configured and ready as published filter matches", () => {
    expect(matchesStatusFilter("READY", "PUBLISHED")).toBe(true);
    expect(matchesStatusFilter("DRAFT", "PUBLISHED")).toBe(false);
  });
});
