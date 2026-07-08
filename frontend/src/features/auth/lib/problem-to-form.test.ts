import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api";
import { applyProblemToForm, formLevelMessage } from "./problem-to-form";

interface TestValues {
  email: string;
  password: string;
}

const KNOWN_FIELDS = ["email", "password"] as const;

function makeApiError(
  overrides: Partial<ConstructorParameters<typeof ApiError>[1]> = {},
): ApiError {
  return new ApiError("failed", {
    status: 422,
    problem: {
      type: "https://api.vzlyot-talantov.ru/problems/validation-error",
      title: "Validation failed",
      status: 422,
      detail: "One or more fields are invalid.",
      errors: [],
    },
    ...overrides,
  });
}

describe("applyProblemToForm", () => {
  it("maps a field error's JSON pointer to setError", () => {
    const setError = vi.fn();
    const error = makeApiError({
      problem: {
        type: "x",
        title: "Validation failed",
        status: 422,
        errors: [{ pointer: "/password", code: "weak-password", detail: "Слишком слабый пароль" }],
      },
    });

    const message = applyProblemToForm<TestValues>(error, { setError, knownFields: KNOWN_FIELDS });

    expect(setError).toHaveBeenCalledWith("password", {
      type: "server",
      message: "Слишком слабый пароль",
    });
    // Every error was field-mapped → no form-level message.
    expect(message).toBeNull();
  });

  it("returns a form-level message when an error maps to no known field", () => {
    const setError = vi.fn();
    const error = makeApiError({
      status: 409,
      problem: {
        type: "conflict",
        title: "Email already in use",
        status: 409,
        detail: "An active account already exists for this email.",
        errors: [],
      },
    });

    const message = applyProblemToForm<TestValues>(error, { setError, knownFields: KNOWN_FIELDS });

    expect(setError).not.toHaveBeenCalled();
    expect(message).toBe("An active account already exists for this email.");
  });

  it("returns a generic message for a non-ApiError", () => {
    const setError = vi.fn();
    const message = applyProblemToForm<TestValues>(new Error("boom"), {
      setError,
      knownFields: KNOWN_FIELDS,
    });
    expect(message).toBe("Произошла непредвиденная ошибка. Повторите попытку.");
  });
});

describe("formLevelMessage", () => {
  it("describes a connectivity failure (status 0)", () => {
    const error = new ApiError("timeout", { status: 0 });
    expect(formLevelMessage(error)).toContain("сервером");
  });

  it("describes a rate-limit (429)", () => {
    const error = new ApiError("too many", { status: 429 });
    expect(formLevelMessage(error)).toContain("Слишком много попыток");
  });

  it("prefers the problem detail when present", () => {
    const error = makeApiError({
      problem: { type: "x", title: "T", status: 422, detail: "Точная причина" },
    });
    expect(formLevelMessage(error)).toBe("Точная причина");
  });
});
