import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Radio, RadioGroup } from "./radio";

function Fixture(props: { disabled?: boolean; defaultValue?: string }) {
  return (
    <RadioGroup
      label="Тариф"
      {...(props.defaultValue != null ? { defaultValue: props.defaultValue } : {})}
    >
      <Radio value="free" label="Бесплатный" />
      <Radio value="pro" label="Профессиональный" disabled={props.disabled} />
      <Radio value="team" label="Командный" />
    </RadioGroup>
  );
}

describe("RadioGroup", () => {
  it("renders all options as radios", () => {
    render(<Fixture />);
    expect(screen.getAllByRole("radio")).toHaveLength(3);
    expect(screen.getByRole("radio", { name: "Бесплатный" })).toBeInTheDocument();
  });

  it("selects an option on click", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    const option = screen.getByRole("radio", { name: "Командный" });
    await user.click(option);
    expect(option).toBeChecked();
  });

  it("selects by clicking the label", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    await user.click(screen.getByText("Бесплатный"));
    expect(screen.getByRole("radio", { name: "Бесплатный" })).toBeChecked();
  });

  it("allows only one selection at a time", async () => {
    const user = userEvent.setup();
    render(<Fixture defaultValue="free" />);
    await user.click(screen.getByRole("radio", { name: "Командный" }));
    expect(screen.getByRole("radio", { name: "Бесплатный" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Командный" })).toBeChecked();
  });

  it("supports arrow-key navigation between options", async () => {
    const user = userEvent.setup();
    render(<Fixture defaultValue="free" />);
    screen.getByRole("radio", { name: "Бесплатный" }).focus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("radio", { name: "Профессиональный" })).toHaveFocus();
  });

  it("supports controlled usage", async () => {
    const onValueChange = vi.fn();
    const user = userEvent.setup();
    function Controlled() {
      const [value, setValue] = useState("free");
      return (
        <RadioGroup
          label="Тариф"
          value={value}
          onValueChange={(next) => {
            onValueChange(next);
            setValue(next);
          }}
        >
          <Radio value="free" label="Бесплатный" />
          <Radio value="pro" label="Профессиональный" />
        </RadioGroup>
      );
    }
    render(<Controlled />);
    await user.click(screen.getByRole("radio", { name: "Профессиональный" }));
    expect(onValueChange).toHaveBeenCalledWith("pro");
  });

  it("does not select a disabled option", async () => {
    const user = userEvent.setup();
    render(<Fixture disabled />);
    const option = screen.getByRole("radio", { name: "Профессиональный" });
    await user.click(option);
    expect(option).not.toBeChecked();
    expect(option).toBeDisabled();
  });

  it("marks the group invalid and shows the error message", () => {
    render(
      <RadioGroup label="Тариф" error="Выберите тариф">
        <Radio value="free" label="Бесплатный" />
      </RadioGroup>,
    );
    expect(screen.getByRole("radiogroup")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Выберите тариф")).toBeInTheDocument();
  });

  it("forwards a ref to the group root", () => {
    const ref = vi.fn();
    render(
      <RadioGroup ref={ref} label="Тариф">
        <Radio value="free" label="Бесплатный" />
      </RadioGroup>,
    );
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLElement));
  });
});
