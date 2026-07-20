import { describe, expect, it } from "vitest";
import { toSearchParams } from "./api";

describe("toSearchParams", () => {
  it("omits empty and falsy filters", () => {
    expect(toSearchParams({}).toString()).toBe("");
    expect(toSearchParams({ q: "  ", gender: "", hasDocuments: false }).toString()).toBe("");
  });

  it("trims text filters and serializes set values", () => {
    const params = toSearchParams({
      q: "  Иванов ",
      gender: "female",
      ageMin: "7",
      ageMax: "12",
      competitionId: "comp-1",
      participantType: "solo",
      hasDocuments: true,
    });
    expect(params.get("q")).toBe("Иванов");
    expect(params.get("gender")).toBe("female");
    expect(params.get("ageMin")).toBe("7");
    expect(params.get("ageMax")).toBe("12");
    expect(params.get("competitionId")).toBe("comp-1");
    expect(params.get("participantType")).toBe("solo");
    expect(params.get("hasDocuments")).toBe("true");
  });
});
