import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { TimePicker } from "./time-picker";

function Controlled({ initial = "" }: { initial?: string }): React.JSX.Element {
  const [value, setValue] = useState(initial);
  return (
    <>
      <TimePicker label="Время" value={value} onChange={setValue} />
      <output data-testid="value">{value}</output>
    </>
  );
}

describe("TimePicker", () => {
  it("renders no native time input, whose popup the browser owns", () => {
    render(<TimePicker label="Время" value="11:47" onChange={vi.fn()} />);

    // Same reason the month and year dropdowns had to be replaced: a native
    // control's popup is drawn outside the page and takes no styling at all.
    expect(document.querySelector('input[type="time"]')).toBeNull();
  });

  it("lets the time be typed as four digits", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByLabelText("Время"), "1147");

    expect(screen.getByLabelText("Время")).toHaveValue("11:47");
    expect(screen.getByTestId("value")).toHaveTextContent("11:47");
  });

  it("stays quiet while the digits are not yet a time", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TimePicker label="Время" value="" onChange={onChange} />);

    await user.type(screen.getByLabelText("Время"), "11");

    // "11" is a state worth showing and not an answer worth reporting.
    expect(screen.getByLabelText("Время")).toHaveValue("11");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("steps the half the caret is in with the arrow keys", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="11:47" />);

    const field = screen.getByLabelText<HTMLInputElement>("Время");
    await user.click(field);
    // The caret decides which half steps, so it is placed rather than assumed.
    field.setSelectionRange(0, 0);
    await user.keyboard("{ArrowUp}");

    expect(screen.getByTestId("value")).toHaveTextContent("12:47");
  });

  it("wraps at the end of the day rather than stopping there", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="23:30" />);

    const field = screen.getByLabelText<HTMLInputElement>("Время");
    await user.click(field);
    // The caret decides which half steps, so it is placed rather than assumed.
    field.setSelectionRange(0, 0);
    await user.keyboard("{ArrowUp}");

    expect(screen.getByTestId("value")).toHaveTextContent("00:30");
  });

  it("resolves a half-typed value when the field is left", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByLabelText("Время"), "11");
    await user.tab();

    // Leaving "11" on screen would look saved when nothing was.
    expect(screen.getByLabelText("Время")).toHaveValue("");
  });

  it("picks an hour and a minute from the columns", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="11:47" />);

    await user.click(screen.getByRole("button", { name: "Выбрать время" }));
    await user.click(within(screen.getByRole("group", { name: "Часы" })).getByText("09"));

    expect(screen.getByTestId("value")).toHaveTextContent("09:47");

    await user.click(within(screen.getByRole("group", { name: "Минуты" })).getByText("15"));

    expect(screen.getByTestId("value")).toHaveTextContent("09:15");
  });

  it("offers minutes at the step it was given", async () => {
    const user = userEvent.setup();
    render(<TimePicker label="Время" value="10:00" onChange={vi.fn()} minuteStep={15} />);

    await user.click(screen.getByRole("button", { name: "Выбрать время" }));
    const minutes = within(screen.getByRole("group", { name: "Минуты" })).getAllByRole("button");

    expect(minutes.map((button) => button.textContent)).toEqual(["00", "15", "30", "45"]);
  });

  it("reports an empty value once the field is emptied", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="11:47" />);

    await user.clear(screen.getByLabelText("Время"));

    expect(screen.getByTestId("value")).toHaveTextContent("");
  });

  it("cannot be opened or typed into when disabled", async () => {
    render(<TimePicker label="Время" value="11:47" onChange={vi.fn()} disabled />);

    expect(screen.getByLabelText("Время")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Выбрать время" })).toBeDisabled();
  });
});
