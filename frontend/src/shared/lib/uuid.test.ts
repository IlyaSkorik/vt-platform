import { describe, expect, it } from "vitest";
import { createUuidV7, isUuidV7 } from "./uuid";

describe("createUuidV7", () => {
  it("returns a UUID v7 string", () => {
    const value = createUuidV7();
    expect(isUuidV7(value)).toBe(true);
    expect(value.charAt(14)).toBe("7");
  });

  it("rejects UUID v4 from crypto.randomUUID", () => {
    expect(isUuidV7(crypto.randomUUID())).toBe(false);
  });
});
