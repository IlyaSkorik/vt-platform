import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Switch } from "./switch";

describe("Switch", () => {
  it("renders with an associated label", () => {
    render(<Switch label="Уведомления" />);
    expect(screen.getByRole("switch", { name: "Уведомления" })).toBeInTheDocument();
  });

  it("toggles when clicked (uncontrolled)", async () => {
    const user = userEvent.setup();
    render(<Switch label="Тёмная тема" />);
    const toggle = screen.getByRole("switch", { name: "Тёмная тема" });
    expect(toggle).not.toBeChecked();
    await user.click(toggle);
    expect(toggle).toBeChecked();
  });

  it("toggles by clicking the label", async () => {
    const user = userEvent.setup();
    render(<Switch label="Автосохранение" />);
    await user.click(screen.getByText("Автосохранение"));
    expect(screen.getByRole("switch")).toBeChecked();
  });

  it("supports controlled usage", async () => {
    const onCheckedChange = vi.fn();
    const user = userEvent.setup();
    function Controlled() {
      const [checked, setChecked] = useState(false);
      return (
        <Switch
          label="Управляемый"
          checked={checked}
          onCheckedChange={(value) => {
            onCheckedChange(value);
            setChecked(value);
          }}
        />
      );
    }
    render(<Controlled />);
    await user.click(screen.getByRole("switch"));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
    expect(screen.getByRole("switch")).toBeChecked();
  });

  it("does not toggle when disabled", async () => {
    const onCheckedChange = vi.fn();
    const user = userEvent.setup();
    render(<Switch label="Выкл" disabled onCheckedChange={onCheckedChange} />);
    await user.click(screen.getByRole("switch"));
    expect(onCheckedChange).not.toHaveBeenCalled();
    expect(screen.getByRole("switch")).toBeDisabled();
  });

  it("supports keyboard activation via Space", async () => {
    const user = userEvent.setup();
    render(<Switch label="Пробел" />);
    const toggle = screen.getByRole("switch");
    toggle.focus();
    await user.keyboard("{ }");
    expect(toggle).toBeChecked();
  });

  it("renders a description associated via aria-describedby", () => {
    render(<Switch label="С описанием" description="Полезный текст" />);
    const toggle = screen.getByRole("switch");
    const describedBy = toggle.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(screen.getByText("Полезный текст")).toHaveAttribute("id", describedBy);
  });

  it("forwards a ref to the underlying control", () => {
    const ref = vi.fn();
    render(<Switch label="Реф" ref={ref} />);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });
});
