import type { Meta, StoryObj } from "@storybook/react-vite";
import { Mail, Search, X } from "lucide-react";
import { Input } from "./input";

const meta = {
  title: "Shared/UI/Input",
  component: Input,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: { disabled: { control: "boolean" }, readOnly: { control: "boolean" } },
  args: { label: "Электронная почта", placeholder: "you@example.com" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Input>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithDescription: Story = { args: { description: "Мы никому не передаём ваш адрес." } };
export const WithError: Story = {
  args: { error: "Введите корректный адрес.", defaultValue: "неверно" },
};
export const WithSuccess: Story = {
  args: { success: "Адрес свободен.", defaultValue: "user@vt.ru" },
};
export const LeadingIcon: Story = { args: { leadingIcon: <Mail />, label: "Почта" } };
export const TrailingIcon: Story = {
  args: { trailingIcon: <Search />, label: "Поиск", placeholder: "Найти…" },
};
export const WithPrefix: Story = {
  args: { prefix: "https://", label: "Сайт", placeholder: "vt.ru" },
};
export const WithSuffix: Story = {
  args: { suffix: "₽", label: "Цена", placeholder: "0", type: "number" },
};
export const Disabled: Story = { args: { disabled: true, defaultValue: "Недоступно" } };
export const ReadOnly: Story = { args: { readOnly: true, defaultValue: "Только чтение" } };
export const Required: Story = { args: { required: true, label: "Обязательное поле" } };
export const WithAction: Story = {
  args: {
    label: "С действием",
    defaultValue: "Очистите меня",
    action: (
      <button
        type="button"
        aria-label="Очистить"
        className="flex items-center rounded-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 [&_svg]:size-4"
      >
        <X aria-hidden="true" />
      </button>
    ),
  },
};
