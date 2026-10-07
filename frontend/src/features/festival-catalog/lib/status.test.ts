import { describe, expect, it } from "vitest";
import { catalogStatusConfig, isPublicStatus } from "./status";

describe("catalogStatusConfig", () => {
  it("enables Apply only when registration is open", () => {
    expect(catalogStatusConfig("REGISTRATION_OPEN").apply).toEqual({
      enabled: true,
      label: "Подать заявку",
    });
  });

  it("states why rather than going quiet when there is nothing to apply to", () => {
    // The slot is never empty: every status puts a sentence where the action
    // would be, so the card keeps its shape and the reader learns the reason.
    expect(catalogStatusConfig("COMING_SOON").apply).toEqual({
      enabled: false,
      label: "Регистрация скоро",
    });
    expect(catalogStatusConfig("REGISTRATION_CLOSED").apply).toEqual({
      enabled: false,
      label: "Регистрация закрыта",
    });
    // A running festival reads as closed registration: the action answers whether
    // an application can be sent, and for both the answer is the same sentence.
    expect(catalogStatusConfig("RUNNING").apply).toEqual({
      enabled: false,
      label: "Регистрация закрыта",
    });
    expect(catalogStatusConfig("COMPLETED").apply).toEqual({
      enabled: false,
      label: "Фестиваль завершён",
    });
  });

  it("falls back gracefully for an unknown status", () => {
    const config = catalogStatusConfig("SOMETHING_NEW");
    expect(config.apply.enabled).toBe(false);
    expect(config.apply.label).toBeTruthy();
    expect(config.label).toBeTruthy();
  });
});

describe("isPublicStatus", () => {
  it("recognizes known statuses", () => {
    expect(isPublicStatus("RUNNING")).toBe(true);
    expect(isPublicStatus("DRAFT")).toBe(false);
  });
});
