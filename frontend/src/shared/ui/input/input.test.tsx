import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Input } from "./input";

describe("Input", () => {
  it("associates the label with the control", () => {
    render(<Input label="Электронная почта" />);
    expect(screen.getByLabelText("Электронная почта")).toBeInTheDocument();
  });

  it("accepts typed input", async () => {
    const user = userEvent.setup();
    render(<Input label="Имя" />);
    const input = screen.getByLabelText("Имя");
    await user.type(input, "Взлёт");
    expect(input).toHaveValue("Взлёт");
  });

  it("marks the field invalid and links the error message", () => {
    render(<Input label="Пароль" error="Слишком короткий" />);
    const input = screen.getByLabelText("Пароль");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Слишком короткий");
  });

  it("links the description via aria-describedby", () => {
    render(<Input label="Логин" description="Минимум 3 символа" />);
    expect(screen.getByLabelText("Логин")).toHaveAccessibleDescription("Минимум 3 символа");
  });

  it("prefers the error over success when both are provided", () => {
    render(<Input label="Поле" error="Ошибка" success="Успех" />);
    expect(screen.getByText("Ошибка")).toBeInTheDocument();
    expect(screen.queryByText("Успех")).not.toBeInTheDocument();
  });

  it("does not accept input when disabled", async () => {
    const user = userEvent.setup();
    render(<Input label="Отключено" disabled />);
    const input = screen.getByLabelText("Отключено");
    await user.type(input, "abc");
    expect(input).toHaveValue("");
    expect(input).toBeDisabled();
  });

  it("is read-only when readOnly is set", () => {
    render(<Input label="Только чтение" readOnly value="фикс" onChange={() => {}} />);
    expect(screen.getByLabelText("Только чтение")).toHaveAttribute("readonly");
  });

  it("forwards a ref to the input element", () => {
    let node: HTMLInputElement | null = null;
    render(
      <Input
        label="Реф"
        ref={(el) => {
          node = el;
        }}
      />,
    );
    expect(node).toBeInstanceOf(HTMLInputElement);
  });
});
