import { describe, expect, it } from "vitest";
import { createUuidV7, isUuidV7, timestampFromUuidV7 } from "./uuid";

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

describe("timestampFromUuidV7", () => {
  it("reads the embedded timestamp from a fresh UUID v7", () => {
    const before = Date.now();
    const value = createUuidV7();
    const after = Date.now();
    const date = timestampFromUuidV7(value);
    expect(date).not.toBeNull();
    if (date == null) {
      return;
    }
    expect(date.getTime()).toBeGreaterThanOrEqual(before - 5);
    expect(date.getTime()).toBeLessThanOrEqual(after + 5);
  });

  it("returns null for non-v7 ids", () => {
    expect(timestampFromUuidV7(crypto.randomUUID())).toBeNull();
  });
});
