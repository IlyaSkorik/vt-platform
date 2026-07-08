import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Checkbox } from "./checkbox";

describe("Checkbox", () => {
  it("renders with an associated label", () => {
    render(<Checkbox label="Согласен" />);
    expect(screen.getByRole("checkbox", { name: "Согласен" })).toBeInTheDocument();
  });

  it("toggles when clicked (uncontrolled)", async () => {
    const user = userEvent.setup();
    render(<Checkbox label="Опция" />);
    const checkbox = screen.getByRole("checkbox", { name: "Опция" });
    expect(checkbox).not.toBeChecked();
    await user.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  it("toggles by clicking the label", async () => {
    const user = userEvent.setup();
    render(<Checkbox label="Кликни меня" />);
    await user.click(screen.getByText("Кликни меня"));
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("supports controlled usage", async () => {
    const onCheckedChange = vi.fn();
    const user = userEvent.setup();
    function Controlled() {
      const [checked, setChecked] = useState(false);
      return (
        <Checkbox
          label="Управляемый"
          checked={checked}
          onCheckedChange={(value) => {
            onCheckedChange(value);
            setChecked(value === true);
          }}
        />
      );
    }
    render(<Controlled />);
    await user.click(screen.getByRole("checkbox"));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("renders the indeterminate state", () => {
    render(<Checkbox label="Частично" checked="indeterminate" />);
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-checked", "mixed");
  });

  it("does not toggle when disabled", async () => {
    const onCheckedChange = vi.fn();
    const user = userEvent.setup();
    render(<Checkbox label="Выкл" disabled onCheckedChange={onCheckedChange} />);
    await user.click(screen.getByRole("checkbox"));
    expect(onCheckedChange).not.toHaveBeenCalled();
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });

  it("supports keyboard activation via Space", async () => {
    const user = userEvent.setup();
    render(<Checkbox label="Пробел" />);
    const checkbox = screen.getByRole("checkbox");
    checkbox.focus();
    await user.keyboard("{ }");
    expect(checkbox).toBeChecked();
  });

  it("marks the control invalid and shows the error message", () => {
    render(<Checkbox label="С ошибкой" error="Обязательно" />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Обязательно")).toBeInTheDocument();
  });

  it("renders a description associated via aria-describedby", () => {
    render(<Checkbox label="С описанием" description="Полезный текст" />);
    const checkbox = screen.getByRole("checkbox");
    const describedBy = checkbox.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(screen.getByText("Полезный текст")).toHaveAttribute("id", describedBy);
  });

  it("forwards a ref to the underlying control", () => {
    const ref = vi.fn();
    render(<Checkbox label="Реф" ref={ref} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });
});
