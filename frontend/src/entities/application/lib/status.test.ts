import { describe, expect, it } from "vitest";

import { applicationStatusPresentation, submissionStatusPresentation } from "./status";

describe("applicationStatusPresentation", () => {
  it("maps known statuses to a label and badge variant", () => {
    expect(applicationStatusPresentation("DRAFT")).toEqual({
      label: "Черновик",
      variant: "neutral",
    });
    expect(applicationStatusPresentation("WAITING_PAYMENT")).toEqual({
      label: "Ожидает оплаты",
      variant: "warning",
    });
    expect(applicationStatusPresentation("PAID")).toEqual({
      label: "Оплачена",
      variant: "success",
    });
    expect(applicationStatusPresentation("CANCELLED")).toEqual({
      label: "Отменена",
      variant: "danger",
    });
  });

  it("falls back for an unknown status", () => {
    expect(applicationStatusPresentation("WAT")).toEqual({ label: "—", variant: "neutral" });
  });
});

describe("submissionStatusPresentation", () => {
  it("maps per-performance statuses", () => {
    expect(submissionStatusPresentation("APPROVED")).toEqual({
      label: "Одобрена",
      variant: "success",
    });
    expect(submissionStatusPresentation("REQUIRES_CORRECTION")).toEqual({
      label: "Требует правок",
      variant: "warning",
    });
  });
});
