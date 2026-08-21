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

  it("keeps a long value on one line instead of growing the trigger", async () => {
    // The reported bug: a value too wide for the control wrapped onto a second line,
    // so this trigger alone grew taller than the fields beside it and the text spilled
    // out of the border. Tailwind utilities are the mechanism and jsdom cannot compute
    // them, so this pins the contract: the value is the trigger's own span child, and
    // the trigger is the element that constrains it.
    render(
      <Select
        label="Шрифт"
        options={[{ value: "montserrat", label: "Montserrat (нет в библиотеке)" }]}
        defaultValue="montserrat"
      />,
    );
    const trigger = screen.getByRole("combobox");
    const value = trigger.firstElementChild;

    expect(value?.tagName).toBe("SPAN");
    expect(value).toHaveTextContent("Montserrat (нет в библиотеке)");
    expect(trigger.className).toContain("[&>span]:truncate");
    // A flex child will not shrink below its content without this.
    expect(trigger.className).toContain("[&>span]:min-w-0");
  });

  it("still offers the whole label in the open listbox", async () => {
    // Truncating the trigger is only acceptable because nothing is lost: the full text
    // is one click away, and the listbox is free to be wider than the control.
    const user = userEvent.setup();
    render(
      <Select
        label="Шрифт"
        options={[{ value: "montserrat", label: "Montserrat (нет в библиотеке)" }]}
        placeholder="Выберите"
      />,
    );
    await user.click(screen.getByRole("combobox"));

    expect(
      await screen.findByRole("option", { name: "Montserrat (нет в библиотеке)" }),
    ).toBeInTheDocument();
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
