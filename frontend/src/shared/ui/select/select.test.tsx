import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Select } from "./select";
import type { SelectOption } from "./types";

Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};
window.HTMLElement.prototype.scrollIntoView = () => {};

const options: SelectOption[] = [
  { value: "apple", label: "Яблоко" },
  { value: "banana", label: "Банан" },
  { value: "cherry", label: "Вишня", disabled: true },
];

describe("Select", () => {
  it("renders a trigger with an accessible name from its label", () => {
    render(<Select label="Фрукт" options={options} placeholder="Выберите" />);
    expect(screen.getByRole("combobox", { name: "Фрукт" })).toBeInTheDocument();
  });

  it("shows the placeholder when no value is selected", () => {
    render(<Select label="Фрукт" options={options} placeholder="Выберите фрукт" />);
    expect(screen.getByText("Выберите фрукт")).toBeInTheDocument();
  });

  it("renders the current value when defaultValue is set", () => {
    render(<Select label="Фрукт" options={options} defaultValue="banana" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("Банан");
  });

  it("opens the listbox and selects an option", async () => {
    const onValueChange = vi.fn();
    const user = userEvent.setup();
    render(
      <Select
        label="Фрукт"
        options={options}
        placeholder="Выберите"
        onValueChange={onValueChange}
      />,
    );
    await user.click(screen.getByRole("combobox"));
    await user.click(await screen.findByRole("option", { name: "Яблоко" }));
    expect(onValueChange).toHaveBeenCalledWith("apple");
  });

  it("marks the trigger invalid and shows the error message", () => {
    render(<Select label="Фрукт" options={options} error="Выберите фрукт" />);
    expect(screen.getByRole("combobox")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Выберите фрукт")).toBeInTheDocument();
  });

  it("renders a description associated via aria-describedby", () => {
    render(<Select label="Фрукт" options={options} description="Свежие фрукты" />);
    const trigger = screen.getByRole("combobox");
    const describedBy = trigger.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(screen.getByText("Свежие фрукты")).toHaveAttribute("id", describedBy);
  });

  it("marks the field as required with an asterisk", () => {
    render(<Select label="Фрукт" options={options} required />);
    expect(screen.getByText("*")).toBeInTheDocument();
  });

  it("disables the trigger when disabled", () => {
    render(<Select label="Фрукт" options={options} disabled />);
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("forwards a ref to the trigger element", () => {
    const ref = vi.fn();
    render(<Select ref={ref} label="Фрукт" options={options} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLElement));
  });
});
