import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { PasswordInput } from "./password-input";

describe("PasswordInput", () => {
  it("hides the value by default", () => {
    render(<PasswordInput label="Пароль" />);
    expect(screen.getByLabelText("Пароль")).toHaveAttribute("type", "password");
  });

  it("reveals and hides the value via the toggle", async () => {
    const user = userEvent.setup();
    render(<PasswordInput label="Пароль" />);
    const input = screen.getByLabelText("Пароль");
    const toggle = screen.getByRole("button", { name: "Показать пароль" });

    await user.click(toggle);
    expect(input).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Скрыть пароль" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Скрыть пароль" }));
    expect(input).toHaveAttribute("type", "password");
  });

  it("reflects visibility state via aria-pressed", async () => {
    const user = userEvent.setup();
    render(<PasswordInput label="Пароль" />);
    const toggle = screen.getByRole("button");
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
  });

  it("disables the toggle when the field is disabled", () => {
    render(<PasswordInput label="Пароль" disabled />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("surfaces error state from the underlying field", () => {
    render(<PasswordInput label="Пароль" error="Обязательное поле" />);
    expect(screen.getByLabelText("Пароль")).toHaveAttribute("aria-invalid", "true");
  });
});
