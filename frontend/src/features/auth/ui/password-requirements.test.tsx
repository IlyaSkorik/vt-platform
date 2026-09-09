import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PASSWORD_ALPHABET_MESSAGE, PASSWORD_RULES, passwordSchema } from "../model/schemas";
import { PasswordRequirements, passwordFieldError } from "./password-requirements";

/** Long and lowercase: two rules in, three still to go. */
const PARTIAL_PASSWORD = "longenoughpass";
/** Every rule satisfied. */
const COMPLETE_PASSWORD = "StrongPass123!";

/** The row carrying a rule, so its state can be read the way the user sees it. */
function rowFor(label: string): HTMLElement {
  const row = screen.getByText(label).closest("li");
  if (row == null) {
    throw new Error(`No requirement row for "${label}".`);
  }
  return row;
}

describe("PasswordRequirements", () => {
  it("lists every rule of the policy, so none has to be discovered from a rejection", () => {
    render(<PasswordRequirements value="" />);

    expect(screen.getAllByRole("listitem")).toHaveLength(PASSWORD_RULES.length);
    for (const rule of PASSWORD_RULES) {
      expect(screen.getByText(rule.label)).toBeInTheDocument();
    }
  });

  it("ticks off what the password satisfies and announces the state, not just colours it", () => {
    render(<PasswordRequirements value={PARTIAL_PASSWORD} />);

    expect(rowFor("Не менее 12 символов")).toHaveTextContent("Не менее 12 символов — выполнено");
    expect(rowFor("Строчная латинская буква (a–z)")).toHaveTextContent("— выполнено");
    expect(rowFor("Заглавная латинская буква (A–Z)")).toHaveTextContent("— не выполнено");
    expect(rowFor("Цифра (0–9)")).toHaveTextContent("Цифра (0–9) — не выполнено");
    expect(rowFor("Специальный символ (например ! ? @ #)")).toHaveTextContent("— не выполнено");
  });

  it("a fully ticked list is a password the validator accepts", () => {
    // The point of building both from PASSWORD_RULES: a checklist that can be
    // completed and still rejected is worse than no checklist at all.
    render(<PasswordRequirements value={COMPLETE_PASSWORD} />);

    for (const rule of PASSWORD_RULES) {
      expect(rowFor(rule.label)).toHaveTextContent(`${rule.label} — выполнено`);
    }
    expect(passwordSchema.safeParse(COMPLETE_PASSWORD).success).toBe(true);
  });

  it("treats unmet rules as pending until the field is rejected, then as the errors", () => {
    // An empty field greeted by five red lines reads as five mistakes already made.
    const { rerender } = render(<PasswordRequirements value={PARTIAL_PASSWORD} />);

    expect(rowFor("Цифра (0–9)")).toHaveClass("text-muted-foreground");
    expect(rowFor("Цифра (0–9)")).not.toHaveClass("text-danger");

    rerender(<PasswordRequirements value={PARTIAL_PASSWORD} invalid />);

    expect(rowFor("Цифра (0–9)")).toHaveClass("text-danger");
    // What is already done stays done — it is not part of the failure.
    expect(rowFor("Не менее 12 символов")).toHaveClass("text-success");
  });

  it("counts Cyrillic letters towards nothing, because the policy does not accept them", () => {
    // "Пароль" is not a lowercase letter here, and saying so on the rows is what makes
    // the alphabet rule visible before the field is submitted.
    render(<PasswordRequirements value="ОченьДлинныйПароль1!" />);

    expect(rowFor("Строчная латинская буква (a–z)")).toHaveTextContent("— не выполнено");
    expect(rowFor("Заглавная латинская буква (A–Z)")).toHaveTextContent("— не выполнено");
    expect(passwordSchema.safeParse("ОченьДлинныйПароль1!").success).toBe(false);
  });

  it("is announced politely, so a rule ticking off is not silent", () => {
    render(<PasswordRequirements value={PARTIAL_PASSWORD} />);

    expect(screen.getByRole("list")).toHaveAttribute("aria-live", "polite");
  });
});

describe("passwordFieldError", () => {
  it("says nothing when the field is fine", () => {
    expect(passwordFieldError(undefined)).toBeUndefined();
  });

  it("points at the list instead of repeating one of its lines", () => {
    for (const rule of PASSWORD_RULES) {
      expect(passwordFieldError({ type: "custom", message: rule.message })).toBe(
        "Пароль не соответствует требованиям ниже",
      );
    }
  });

  it("names the alphabet on the field, which is where a mistake is named", () => {
    expect(passwordFieldError({ type: "custom", message: PASSWORD_ALPHABET_MESSAGE })).toBe(
      PASSWORD_ALPHABET_MESSAGE,
    );
  });

  it("shows verbatim what the list cannot say", () => {
    // A breached password the server refused, and a form's own extra rule: neither is
    // in the checklist, so neither can be replaced by a pointer to it.
    expect(passwordFieldError({ type: "server", message: "Пароль найден в утечке." })).toBe(
      "Пароль найден в утечке.",
    );
    expect(
      passwordFieldError({ type: "custom", message: "Новый пароль совпадает с текущим" }),
    ).toBe("Новый пароль совпадает с текущим");
  });
});
