import { describe, expect, it } from "vitest";
import { genderLabel } from "./model";

describe("genderLabel", () => {
  it("maps the backend's uppercase gender values", () => {
    expect(genderLabel("MALE")).toBe("Мужской");
    expect(genderLabel("FEMALE")).toBe("Женский");
    expect(genderLabel("OTHER")).toBe("Другой");
  });

  it("is tolerant of case", () => {
    expect(genderLabel("male")).toBe("Мужской");
  });

  it("falls back to a dash for null/empty/unknown (never 'undefined')", () => {
    expect(genderLabel(null)).toBe("—");
    expect(genderLabel(undefined)).toBe("—");
    expect(genderLabel("")).toBe("—");
    expect(genderLabel("xyz")).toBe("—");
  });
});
