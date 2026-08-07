import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { DatePicker, DateTimePicker } from "./date-picker";

const meta = {
  title: "Shared/UI/DatePicker",
  component: DatePicker,
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          'Заменяет `<input type="date">`, внешний вид которого целиком принадлежит браузеру. ' +
          "Значение на проводе прежнее — `YYYY-MM-DD`, — поэтому подмена контрола не трогает формы.",
      },
    },
  },
  tags: ["autodocs"],
} satisfies Meta<typeof DatePicker>;

export default meta;
type Story = StoryObj<typeof meta>;

function Demo({
  initial = "",
  ...props
}: { initial?: string } & Partial<React.ComponentProps<typeof DatePicker>>): React.JSX.Element {
  const [value, setValue] = useState(initial);
  return (
    <div className="w-72">
      <DatePicker label="Дата" value={value} onChange={setValue} {...props} />
      <p className="mt-2 text-muted-foreground text-xs">
        Значение: <code>{value || "—"}</code>
      </p>
    </div>
  );
}

export const Empty: Story = {
  args: { value: "", onChange: () => {} },
  render: () => <Demo />,
};

export const WithValue: Story = {
  args: { value: "", onChange: () => {} },
  render: () => <Demo initial="2026-05-20" />,
};

/** Год выбирается выпадающим списком — иначе до 2014-го пришлось бы листать 130 месяцев. */
export const BirthDate: Story = {
  args: { value: "", onChange: () => {} },
  render: () => (
    <Demo initial="2014-05-17" label="Дата рождения" required toYear={new Date().getFullYear()} />
  ),
};

export const WithError: Story = {
  args: { value: "", onChange: () => {} },
  render: () => <Demo label="Дата рождения" required error="Укажите дату рождения" />,
};

export const Disabled: Story = {
  args: { value: "", onChange: () => {} },
  render: () => <Demo initial="2026-05-20" disabled />,
};

/** Дата мышкой, время с клавиатуры: номера в программе стоят в 11:47, а не по слотам. */
export const DateAndTime: Story = {
  args: { value: "", onChange: () => {} },
  render: function DateTimeDemo() {
    const [value, setValue] = useState("2026-05-20T18:30");
    return (
      <div className="w-96">
        <DateTimePicker label="Начало программы" value={value} onChange={setValue} />
        <p className="mt-2 text-muted-foreground text-xs">
          Значение: <code>{value || "—"}</code>
        </p>
      </div>
    );
  },
};
