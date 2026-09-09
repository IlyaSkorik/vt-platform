import { describe, expect, it } from "vitest";
import {
  forgotPasswordSchema,
  loginSchema,
  PASSWORD_ALPHABET_MESSAGE,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  PASSWORD_RULES,
  registerSchema,
  resetPasswordSchema,
} from "./schemas";

const STRONG_PASSWORD = "SuperSecret123!";

describe("loginSchema", () => {
  it("accepts a valid credential set", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "anything",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({
      email: "not-an-email",
      password: "x",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an empty password", () => {
    const result = loginSchema.safeParse({
      email: "user@example.com",
      password: "",
    });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  const base = {
    firstName: "Ирина",
    lastName: "Смирнова",
    email: "irina@example.com",
    password: STRONG_PASSWORD,
    confirmPassword: STRONG_PASSWORD,
    acceptTerms: true as const,
    acceptMarketing: false,
  };

  it("accepts a complete, valid registration", () => {
    expect(registerSchema.safeParse(base).success).toBe(true);
  });

  it(`requires a password of at least ${PASSWORD_MIN_LENGTH} characters`, () => {
    const result = registerSchema.safeParse({
      ...base,
      password: "Short1",
      confirmPassword: "Short1",
    });
    expect(result.success).toBe(false);
  });

  it("requires mixed case and a digit", () => {
    const result = registerSchema.safeParse({
      ...base,
      password: "alllowercaseletters",
      confirmPassword: "alllowercaseletters",
    });
    expect(result.success).toBe(false);
  });

  it("requires a special symbol, as the server's policy always has", () => {
    // The sentence under the field promised one long before the schema asked for it, so
    // the only way to find out was a 422. The checklist now states it and this enforces it.
    const result = registerSchema.safeParse({
      ...base,
      password: "SuperSecret123",
      confirmPassword: "SuperSecret123",
    });
    expect(result.success).toBe(false);
  });

  it("refuses a Cyrillic password and says so, instead of listing four absent classes", () => {
    const cyrillic = "ОченьДлинныйПароль1!";
    const result = registerSchema.safeParse({
      ...base,
      password: cyrillic,
      confirmPassword: cyrillic,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const first = result.error.issues.find((issue) => issue.path.includes("password"));
      expect(first?.message).toBe(PASSWORD_ALPHABET_MESSAGE);
    }
  });

  it("rejects a password past the server's upper bound", () => {
    const tooLong = `A1!${"a".repeat(PASSWORD_MAX_LENGTH)}`;
    const result = registerSchema.safeParse({
      ...base,
      password: tooLong,
      confirmPassword: tooLong,
    });
    expect(result.success).toBe(false);
  });

  it("reports every unmet rule at once, the way the server does", () => {
    // The checklist shows all of them; a schema that stopped at the first would leave
    // it half-lit and the rest of the work unmentioned.
    const result = registerSchema.safeParse({ ...base, password: "aa", confirmPassword: "aa" });
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.issues
        .filter((issue) => issue.path.includes("password"))
        .map((issue) => issue.message);
      // Short, no uppercase, no digit, no symbol — lowercase is the only rule it meets.
      expect(messages).toHaveLength(PASSWORD_RULES.length - 1);
    }
  });

  it("requires the confirmation to match", () => {
    const result = registerSchema.safeParse({ ...base, confirmPassword: "Mismatch12345" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((issue) => issue.path.includes("confirmPassword"))).toBe(
        true,
      );
    }
  });

  it("requires the agreement to be accepted", () => {
    // The account exists because the person entered the agreement, and its data is
    // processed to perform it (LEGAL-001 §4.4) — so there is nothing to register without.
    const result = registerSchema.safeParse({ ...base, acceptTerms: false });
    expect(result.success).toBe(false);
  });

  it("requires nothing else beyond the agreement and the account fields", () => {
    // No consent is asked for at registration: one that had to be given for the service to
    // work would not be freely given (LEGAL-001 §13.1, §13.2). Marketing is the only other
    // box, and it is optional either way.
    expect(registerSchema.safeParse(base).success).toBe(true);
    expect(registerSchema.safeParse({ ...base, acceptMarketing: true }).success).toBe(true);
  });

  it("treats the newsletter as optional", () => {
    // Refusing it changes nothing about the registration — which is exactly what the
    // published policy promises (LEGAL-001 §4.3).
    expect(registerSchema.safeParse({ ...base, acceptMarketing: false }).success).toBe(true);
    expect(registerSchema.safeParse({ ...base, acceptMarketing: true }).success).toBe(true);
  });

  it("requires a first and last name", () => {
    expect(registerSchema.safeParse({ ...base, firstName: "" }).success).toBe(false);
    expect(registerSchema.safeParse({ ...base, lastName: "" }).success).toBe(false);
  });
});

describe("forgotPasswordSchema", () => {
  it("accepts a valid email", () => {
    expect(forgotPasswordSchema.safeParse({ email: "user@example.com" }).success).toBe(true);
  });

  it("rejects a missing email", () => {
    expect(forgotPasswordSchema.safeParse({ email: "" }).success).toBe(false);
  });
});

describe("resetPasswordSchema", () => {
  it("accepts a valid reset with matching passwords", () => {
    const result = resetPasswordSchema.safeParse({
      token: "reset-token",
      password: STRONG_PASSWORD,
      confirmPassword: STRONG_PASSWORD,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing token", () => {
    const result = resetPasswordSchema.safeParse({
      token: "",
      password: STRONG_PASSWORD,
      confirmPassword: STRONG_PASSWORD,
    });
    expect(result.success).toBe(false);
  });

  it("rejects mismatched passwords", () => {
    const result = resetPasswordSchema.safeParse({
      token: "reset-token",
      password: STRONG_PASSWORD,
      confirmPassword: "Different12345",
    });
    expect(result.success).toBe(false);
  });
});
