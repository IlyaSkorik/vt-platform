import { describe, expect, it } from "vitest";
import type { _TotalPrice } from "@/shared/api/generated/model-applications";
import { applicationTotalLabel } from "./total";

function total(totalAmount: string): _TotalPrice {
  return {
    totalAmount,
    submissionsAmount: totalAmount,
    servicesAmount: "0.00",
    currency: "BYN",
    calculatedAt: "2026-08-17T10:00:00.000Z",
  };
}

describe("applicationTotalLabel", () => {
  it("prints the amount with its currency", () => {
    expect(applicationTotalLabel(total("120.00"))).toBe("120.00 BYN");
  });

  it("has nothing to print without a snapshot", () => {
    expect(applicationTotalLabel(null)).toBeNull();
    expect(applicationTotalLabel(undefined)).toBeNull();
  });

  it("treats a zero total as nothing to charge for", () => {
    expect(applicationTotalLabel(total("0.00"))).toBeNull();
  });

  it("ignores an unparsable amount rather than printing it", () => {
    expect(applicationTotalLabel(total(""))).toBeNull();
    expect(applicationTotalLabel(total("—"))).toBeNull();
  });
});
