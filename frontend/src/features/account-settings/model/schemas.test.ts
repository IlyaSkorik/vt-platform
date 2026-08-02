import { describe, expect, it } from "vitest";

import { changePhoneSchema, normalizePhone } from "./schemas";

describe("normalizePhone", () => {
  it("accepts a Belarusian number written any of the usual ways", () => {
    // All four of these are the same number.
    for (const typed of ["+375 29 123-45-67", "8 (029) 123-45-67", "029 123 45 67", "29 1234567"]) {
      expect(normalizePhone(typed)).toBe("+375291234567");
    }
  });

  it("handles the trunk prefix in front of the country code", () => {
    expect(normalizePhone("8 375 29 123 45 67")).toBe("+375291234567");
  });

  it("keeps a city number's own code", () => {
    expect(normalizePhone("8 (0152) 12-34-56")).toBe("+375152123456");
  });

  it("leaves something unrecognisable for the schema to refuse", () => {
    // Guessing at a number nobody can dial is worse than saying it is wrong.
    expect(normalizePhone("123")).toBe("+123");
    expect(normalizePhone("")).toBe("");
  });
});

describe("changePhoneSchema", () => {
  it("takes a Belarusian number", () => {
    expect(changePhoneSchema.safeParse({ phone: "+375291234567" }).success).toBe(true);
  });

  it("refuses a number from anywhere else", () => {
    // Belarus is where the festivals are; an organizer dials nowhere else.
    for (const phone of ["+79991234567", "+380671234567", "+14155552671"]) {
      expect(changePhoneSchema.safeParse({ phone }).success).toBe(false);
    }
  });

  it("refuses a Belarusian number of the wrong length", () => {
    expect(changePhoneSchema.safeParse({ phone: "+37529123456" }).success).toBe(false);
    expect(changePhoneSchema.safeParse({ phone: "+3752912345678" }).success).toBe(false);
  });
});
