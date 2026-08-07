import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { DatePicker, DateTimePicker } from "./date-picker";

function Controlled({ initial = "" }: { initial?: string }): React.JSX.Element {
  const [value, setValue] = useState(initial);
  return (
    <>
      <DatePicker label="Дата рождения" value={value} onChange={setValue} />
      <output data-testid="value">{value}</output>
    </>
  );
}

describe("DatePicker", () => {
  it("shows the placeholder until a date is chosen", () => {
    render(<DatePicker label="Дата" value="" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Выберите дату/ })).toBeInTheDocument();
  });

  it("shows the chosen date in the language it is read in", () => {
    render(<DatePicker label="Дата" value="2015-04-01" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /апреля 2015/ })).toBeInTheDocument();
  });

  it("reports the day the user clicks in the wire format", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="2026-05-20" />);

    await user.click(screen.getByRole("button", { name: /мая 2026/ }));
    // Found by its visible text inside the grid: the library gives each day
    // button a full spoken label ("7 мая 2026 г."), which is right for a screen
    // reader and not what a test should be spelling out.
    await user.click(within(screen.getByRole("grid")).getByText("7"));

    expect(screen.getByTestId("value")).toHaveTextContent("2026-05-07");
  });

  it("closes once a day is picked, rather than leaving the calendar in the way", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="2026-05-20" />);

    await user.click(screen.getByRole("button", { name: /мая 2026/ }));
    await user.click(within(screen.getByRole("grid")).getByText("7"));

    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
  });

  it("can be cleared, and offers no way to clear what is already empty", () => {
    const { rerender } = render(<DatePicker label="Дата" value="2026-05-20" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Очистить дату" })).toBeInTheDocument();

    rerender(<DatePicker label="Дата" value="" onChange={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Очистить дату" })).not.toBeInTheDocument();
  });

  it("reports an empty value when cleared", async () => {
    const user = userEvent.setup();
    render(<Controlled initial="2026-05-20" />);

    await user.click(screen.getByRole("button", { name: "Очистить дату" }));

    expect(screen.getByTestId("value")).toHaveTextContent("");
  });

  it("wires the error to the trigger so a screen reader hears it", () => {
    render(<DatePicker label="Дата" value="" onChange={vi.fn()} error="Укажите дату" />);

    const trigger = screen.getByRole("button", { name: /Выберите дату/ });
    expect(trigger).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Укажите дату")).toBeInTheDocument();
    expect(trigger.getAttribute("aria-describedby")).toContain("message");
  });

  it("navigates months and years with the platform's own select, not the browser's", async () => {
    // The reported bug: a native `<select>` popup is drawn by the browser, takes
    // no token and ignored the theme — on dark it was white text on a white list.
    // No stylesheet can reach that popup, so the only fix is not to render one.
    const user = userEvent.setup();
    render(<Controlled initial="2026-05-20" />);

    await user.click(screen.getByRole("button", { name: /мая 2026/ }));

    expect(document.querySelectorAll("select")).toHaveLength(0);
    // Radix renders each as a combobox: month and year.
    expect(screen.getAllByRole("combobox")).toHaveLength(2);
  });

  it("does not open when disabled", async () => {
    const user = userEvent.setup();
    render(<DatePicker label="Дата" value="" onChange={vi.fn()} disabled />);

    await user.click(screen.getByRole("button", { name: /Выберите дату/ }));

    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
  });
});

function ControlledDateTime({ initial = "" }: { initial?: string }): React.JSX.Element {
  const [value, setValue] = useState(initial);
  return (
    <>
      <DateTimePicker label="Начало" value={value} onChange={setValue} />
      <output data-testid="value">{value}</output>
    </>
  );
}

describe("DateTimePicker", () => {
  it("splits an existing value across the two controls", () => {
    render(<DateTimePicker label="Начало" value="2026-05-20T18:30" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /мая 2026/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Время")).toHaveValue("18:30");
  });

  it("keeps the time when the day changes", async () => {
    const user = userEvent.setup();
    render(<ControlledDateTime initial="2026-05-20T18:30" />);

    await user.click(screen.getByRole("button", { name: /мая 2026/ }));
    await user.click(within(screen.getByRole("grid")).getByText("7"));

    expect(screen.getByTestId("value")).toHaveTextContent("2026-05-07T18:30");
  });

  it("holds the time field inert until there is a day to attach it to", () => {
    render(<DateTimePicker label="Начало" value="" onChange={vi.fn()} />);

    // A time with no date names no instant, so accepting one would only produce
    // a value that cannot be saved.
    expect(screen.getByLabelText("Время")).toBeDisabled();
  });
});
