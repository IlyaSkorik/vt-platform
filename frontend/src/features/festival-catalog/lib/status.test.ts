import { describe, expect, it } from "vitest";
import { catalogStatusConfig, isPublicStatus } from "./status";

describe("catalogStatusConfig", () => {
  it("enables Apply only when registration is open", () => {
    expect(catalogStatusConfig("REGISTRATION_OPEN").apply).toMatchObject({
      visible: true,
      enabled: true,
    });
  });

  it("shows a disabled Apply for coming-soon and closed", () => {
    expect(catalogStatusConfig("COMING_SOON").apply).toMatchObject({
      visible: true,
      enabled: false,
    });
    expect(catalogStatusConfig("REGISTRATION_CLOSED").apply).toMatchObject({
      visible: true,
      enabled: false,
    });
  });

  it("hides Apply for running and completed festivals", () => {
    expect(catalogStatusConfig("RUNNING").apply.visible).toBe(false);
    expect(catalogStatusConfig("COMPLETED").apply.visible).toBe(false);
  });

  it("falls back gracefully for an unknown status", () => {
    const config = catalogStatusConfig("SOMETHING_NEW");
    expect(config.apply.visible).toBe(false);
    expect(config.label).toBeTruthy();
  });
});

describe("isPublicStatus", () => {
  it("recognizes known statuses", () => {
    expect(isPublicStatus("RUNNING")).toBe(true);
    expect(isPublicStatus("DRAFT")).toBe(false);
  });
});
