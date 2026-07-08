import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Textarea } from "./textarea";

describe("Textarea", () => {
  it("associates the label with the control", () => {
    render(<Textarea label="Комментарий" />);
    expect(screen.getByLabelText("Комментарий")).toBeInTheDocument();
  });

  it("accepts typed input", async () => {
    const user = userEvent.setup();
    render(<Textarea label="Заметка" />);
    const field = screen.getByLabelText("Заметка");
    await user.type(field, "Привет");
    expect(field).toHaveValue("Привет");
  });

  it("marks the field invalid and links the error message", () => {
    render(<Textarea label="Био" error="Слишком длинное" />);
    const field = screen.getByLabelText("Био");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription("Слишком длинное");
  });

  it("links the description via aria-describedby", () => {
    render(<Textarea label="О себе" description="До 500 символов" />);
    expect(screen.getByLabelText("О себе")).toHaveAccessibleDescription("До 500 символов");
  });

  it("does not accept input when disabled", async () => {
    const user = userEvent.setup();
    render(<Textarea label="Отключено" disabled />);
    const field = screen.getByLabelText("Отключено");
    await user.type(field, "abc");
    expect(field).toHaveValue("");
    expect(field).toBeDisabled();
  });

  it("forwards a ref to the textarea element", () => {
    let node: HTMLTextAreaElement | null = null;
    render(
      <Textarea
        label="Реф"
        ref={(el) => {
          node = el;
        }}
      />,
    );
    expect(node).toBeInstanceOf(HTMLTextAreaElement);
  });
});
