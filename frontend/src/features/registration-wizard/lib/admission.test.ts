import { describe, expect, it } from "vitest";

import type { RegistrationAdmissionRule } from "@/shared/api/generated/model-public-catalog";

import {
  admissibleValues,
  ageInYears,
  clearDownstream,
  isFullyAdmissible,
  needsAgeComposition,
  recommendedAgeCategoryId,
} from "./admission";

function rule(
  nominationId: string,
  disciplineId: string,
  ageCategoryId: string,
  participantGroupId: string,
  participationFormatId: string,
): RegistrationAdmissionRule {
  return { nominationId, disciplineId, ageCategoryId, participantGroupId, participationFormatId };
}

const RULES: RegistrationAdmissionRule[] = [
  rule("vocal", "solo", "kids", "one", "live"),
  rule("vocal", "solo", "teens", "one", "live"),
  rule("vocal", "duet", "teens", "two", "live"),
  rule("dance", "modern", "kids", "group", "online"),
];

describe("admissibleValues", () => {
  it("lists nominations that appear in the rules", () => {
    expect(admissibleValues(RULES, {}, "nominationId")).toEqual(new Set(["vocal", "dance"]));
  });

  it("filters disciplines by the chosen nomination", () => {
    expect(admissibleValues(RULES, { nominationId: "vocal" }, "disciplineId")).toEqual(
      new Set(["solo", "duet"]),
    );
    expect(admissibleValues(RULES, { nominationId: "dance" }, "disciplineId")).toEqual(
      new Set(["modern"]),
    );
  });

  it("filters age categories by nomination + discipline", () => {
    expect(
      admissibleValues(RULES, { nominationId: "vocal", disciplineId: "solo" }, "ageCategoryId"),
    ).toEqual(new Set(["kids", "teens"]));
    expect(
      admissibleValues(RULES, { nominationId: "vocal", disciplineId: "duet" }, "ageCategoryId"),
    ).toEqual(new Set(["teens"]));
  });

  it("narrows participant groups and formats to the chosen path", () => {
    const sel = { nominationId: "vocal", disciplineId: "duet", ageCategoryId: "teens" };
    expect(admissibleValues(RULES, sel, "participantGroupId")).toEqual(new Set(["two"]));
    expect(
      admissibleValues(RULES, { ...sel, participantGroupId: "two" }, "participationFormatId"),
    ).toEqual(new Set(["live"]));
  });
});

describe("clearDownstream", () => {
  it("clears axes after the changed one", () => {
    const selection = {
      nominationId: "vocal",
      disciplineId: "solo",
      ageCategoryId: "kids",
      participantGroupId: "one",
      participationFormatId: "live",
    };
    expect(clearDownstream(selection, "disciplineId")).toEqual({
      nominationId: "vocal",
      disciplineId: "solo",
    });
  });
});

describe("isFullyAdmissible", () => {
  it("is true only for a complete, covered combination", () => {
    expect(
      isFullyAdmissible(RULES, {
        nominationId: "vocal",
        disciplineId: "solo",
        ageCategoryId: "kids",
        participantGroupId: "one",
        participationFormatId: "live",
      }),
    ).toBe(true);
  });

  it("is false for an incomplete or uncovered combination", () => {
    expect(isFullyAdmissible(RULES, { nominationId: "vocal", disciplineId: "solo" })).toBe(false);
    expect(
      isFullyAdmissible(RULES, {
        nominationId: "vocal",
        disciplineId: "solo",
        ageCategoryId: "kids",
        participantGroupId: "two",
        participationFormatId: "live",
      }),
    ).toBe(false);
  });
});

describe("needsAgeComposition", () => {
  const bands = [
    { id: "kids", type: "STANDARD" },
    { id: "mixed", type: "MIXED" },
  ];

  it("asks for the ages only behind a mixed band", () => {
    expect(needsAgeComposition(bands, "mixed")).toBe(true);
    expect(needsAgeComposition(bands, "kids")).toBe(false);
  });

  it("asks for nothing while no band is chosen or the id is unknown", () => {
    expect(needsAgeComposition(bands, undefined)).toBe(false);
    expect(needsAgeComposition(bands, "gone")).toBe(false);
  });
});

describe("ageInYears", () => {
  it("computes age, birthday-aware", () => {
    expect(ageInYears("2014-05-01", new Date("2026-07-12"))).toBe(12);
    expect(ageInYears("2014-08-01", new Date("2026-07-12"))).toBe(11);
    expect(ageInYears("", new Date("2026-07-12"))).toBeNull();
  });
});

describe("recommendedAgeCategoryId", () => {
  const bands = [
    { id: "kids", minAge: 6, maxAge: 11 },
    { id: "teens", minAge: 12, maxAge: 17 },
  ];

  it("selects the band containing the age", () => {
    expect(recommendedAgeCategoryId(bands, "2014-05-01", new Date("2026-07-12"))).toBe("teens");
    expect(recommendedAgeCategoryId(bands, "2018-01-01", new Date("2026-07-12"))).toBe("kids");
  });

  it("returns undefined when no band matches or the date is empty", () => {
    expect(recommendedAgeCategoryId(bands, "2005-01-01", new Date("2026-07-12"))).toBeUndefined();
    expect(recommendedAgeCategoryId(bands, "", new Date("2026-07-12"))).toBeUndefined();
  });
});
