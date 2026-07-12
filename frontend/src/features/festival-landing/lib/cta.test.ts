import { describe, expect, it } from "vitest";
import { isPublicStatus, landingCta } from "./cta";

describe("landingCta", () => {
  it("makes only an open registration actionable", () => {
    const open = landingCta("REGISTRATION_OPEN");
    expect(open.canApply).toBe(true);
    expect(open.badgeVariant).toBe("success");
  });

  it("shows non-actionable CTAs for every other status", () => {
    for (const status of ["COMING_SOON", "REGISTRATION_CLOSED", "RUNNING", "COMPLETED"]) {
      expect(landingCta(status).canApply).toBe(false);
    }
  });

  it("maps each status to a distinct label", () => {
    expect(landingCta("COMING_SOON").ctaLabel).not.toBe(landingCta("REGISTRATION_CLOSED").ctaLabel);
    expect(landingCta("RUNNING").ctaLabel).not.toBe(landingCta("COMPLETED").ctaLabel);
  });

  it("falls back safely for an unknown status", () => {
    const fallback = landingCta("SOMETHING_ELSE");
    expect(fallback.canApply).toBe(false);
    expect(isPublicStatus("SOMETHING_ELSE")).toBe(false);
    expect(isPublicStatus("REGISTRATION_OPEN")).toBe(true);
  });
});
