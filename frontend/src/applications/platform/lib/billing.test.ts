import { describe, expect, it } from "vitest";

import type { PerformanceFeeTier } from "@/applications/platform/api/platform-api";

import {
  addFeeTierDraft,
  billingModelLabel,
  emptyFeeTierDrafts,
  exampleOrderTotal,
  type FeeTierDraft,
  feeTiersEqual,
  feeTiersToDrafts,
  formatFeeTier,
  formatTierRange,
  parseFeeAmount,
  removeFeeTierDraft,
  tierLowerBound,
  validateFeeTiers,
} from "./billing";

function draft(overrides: Partial<FeeTierDraft> = {}): FeeTierDraft {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    maxParticipants: overrides.maxParticipants ?? "",
    amount: overrides.amount ?? "1.00",
    openEnded: overrides.openEnded ?? false,
  };
}

/** The schedule from the operator's own example: solo 2.50, up to five 4.00, larger 6.00. */
function exampleDrafts(): FeeTierDraft[] {
  return [
    draft({ id: "a", maxParticipants: "1", amount: "2.50" }),
    draft({ id: "b", maxParticipants: "5", amount: "4.00" }),
    draft({ id: "c", maxParticipants: "", amount: "6.00", openEnded: true }),
  ];
}

describe("tierLowerBound", () => {
  it("starts at one and continues where the row above ended", () => {
    const drafts = exampleDrafts();

    expect([0, 1, 2].map((index) => tierLowerBound(drafts, index))).toEqual([1, 2, 6]);
  });

  it("falls back to one while the row above has no bound yet", () => {
    // Half-typed rows must not make the label read NaN.
    expect(tierLowerBound([draft({ maxParticipants: "" }), draft()], 1)).toBe(1);
  });
});

describe("validateFeeTiers", () => {
  it("derives every lower bound, so the payload has no gaps or overlaps", () => {
    const { errors, tiers } = validateFeeTiers(exampleDrafts());

    expect(errors).toEqual({});
    expect(tiers).toEqual([
      { minParticipants: 1, maxParticipants: 1, amount: "2.50" },
      { minParticipants: 2, maxParticipants: 5, amount: "4.00" },
      { minParticipants: 6, maxParticipants: null, amount: "6.00" },
    ]);
  });

  it("refuses a bound that leaves the band empty", () => {
    const drafts = [
      draft({ id: "a", maxParticipants: "5", amount: "2.50" }),
      draft({ id: "b", maxParticipants: "3", amount: "4.00" }),
      draft({ id: "c", amount: "6.00", openEnded: true }),
    ];

    const { errors, tiers } = validateFeeTiers(drafts);

    expect(errors["b.maxParticipants"]).toBe("Не меньше 6");
    expect(tiers).toBeNull();
  });

  it("refuses a price that is not money", () => {
    const { errors, tiers } = validateFeeTiers([
      draft({ id: "a", amount: "дорого", openEnded: true }),
    ]);

    expect(errors["a.amount"]).toBe("Цена вида 2.50");
    expect(tiers).toBeNull();
  });

  it("accepts a free band — zero is a term, not a mistake", () => {
    const { tiers } = validateFeeTiers([draft({ amount: "0", openEnded: true })]);

    expect(tiers).toEqual([{ minParticipants: 1, maxParticipants: null, amount: "0.00" }]);
  });
});

describe("the row list", () => {
  it("starts as a single band covering every performance", () => {
    const drafts = emptyFeeTierDrafts();

    expect(drafts).toHaveLength(1);
    expect(drafts[0]?.openEnded).toBe(true);
  });

  it("adds bands above the open-ended one, so the tail stays open", () => {
    const added = addFeeTierDraft(emptyFeeTierDrafts());

    expect(added).toHaveLength(2);
    expect(added[0]?.maxParticipants).toBe("1");
    expect(added.at(-1)?.openEnded).toBe(true);
  });

  it("never removes the open-ended band — a headcount would go unpriced", () => {
    const drafts = emptyFeeTierDrafts();

    expect(removeFeeTierDraft(drafts, drafts[0]?.id ?? "")).toHaveLength(1);
  });

  it("removes a closed band", () => {
    const drafts = exampleDrafts();

    expect(removeFeeTierDraft(drafts, "b").map((row) => row.id)).toEqual(["a", "c"]);
  });

  it("reads a saved schedule back into rows", () => {
    const drafts = feeTiersToDrafts([
      { minParticipants: 1, maxParticipants: 1, amount: "2.50" },
      { minParticipants: 2, maxParticipants: null, amount: "4.00" },
    ]);

    expect(drafts.map((row) => [row.maxParticipants, row.amount, row.openEnded])).toEqual([
      ["1", "2.50", false],
      ["", "4.00", true],
    ]);
  });
});

describe("formatting", () => {
  it("names each band the way a human reads it", () => {
    expect(formatTierRange(1, 1)).toBe("1 участник");
    expect(formatTierRange(2, 5)).toBe("2–5 участников");
    expect(formatTierRange(2, 3)).toBe("2–3 участника");
    expect(formatTierRange(6, null)).toBe("от 6 участников");
  });

  it("puts the band and its price on one line", () => {
    expect(formatFeeTier({ minParticipants: 1, maxParticipants: 1, amount: "2.50" })).toBe(
      "1 участник — 2.50 BYN",
    );
  });

  it("labels both commercial terms", () => {
    expect(billingModelLabel("COMMISSION_PERCENT")).toBe("Процент от взносов");
    expect(billingModelLabel("PER_PERFORMANCE_FEE")).toBe("Цена за номер");
  });

  it("normalizes a comma and pads the minor unit", () => {
    expect(parseFeeAmount("2,5")).toBe("2.50");
    expect(parseFeeAmount(" 4 ")).toBe("4.00");
    expect(parseFeeAmount("2.505")).toBeNull();
    expect(parseFeeAmount("")).toBeNull();
  });
});

describe("exampleOrderTotal", () => {
  it("prices an order performance by performance", () => {
    // A solo, a duet and an eight-strong ensemble: 2.50 + 4.00 + 6.00.
    const { tiers } = validateFeeTiers(exampleDrafts());

    expect(exampleOrderTotal(tiers ?? [], [1, 2, 8])).toBe("12.50");
  });
});

describe("feeTiersEqual", () => {
  it("sees an unchanged schedule as unchanged", () => {
    const tier: PerformanceFeeTier = { minParticipants: 1, maxParticipants: null, amount: "3.00" };

    expect(feeTiersEqual([tier], [{ ...tier }])).toBe(true);
    expect(feeTiersEqual([tier], [{ ...tier, amount: "4.00" }])).toBe(false);
    expect(feeTiersEqual([tier], [])).toBe(false);
  });
});
