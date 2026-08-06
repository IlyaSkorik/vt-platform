import { describe, expect, it } from "vitest";
import {
  forgotPasswordSchema,
  loginSchema,
  PASSWORD_MIN_LENGTH,
  registerSchema,
  resetPasswordSchema,
} from "./schemas";

const STRONG_PASSWORD = "SuperSecret123";

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
    acceptDataProcessing: true as const,
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

  it("requires the confirmation to match", () => {
    const result = registerSchema.safeParse({ ...base, confirmPassword: "Mismatch12345" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((issue) => issue.path.includes("confirmPassword"))).toBe(
        true,
      );
    }
  });

  it("requires terms acceptance", () => {
    const result = registerSchema.safeParse({ ...base, acceptTerms: false });
    expect(result.success).toBe(false);
  });

  it("requires consent to processing, separately from the terms", () => {
    // Two decisions, not one: a permission bundled with an agreement is not freely
    // given, so ticking the terms alone must not be enough (LEGAL-001 §13.1).
    const result = registerSchema.safeParse({ ...base, acceptDataProcessing: false });
    expect(result.success).toBe(false);
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
