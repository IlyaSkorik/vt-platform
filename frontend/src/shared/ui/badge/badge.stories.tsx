import type { Meta, StoryObj } from "@storybook/react-vite";
import { Check, Star } from "lucide-react";
import { Badge } from "./badge";

const meta = {
  title: "Shared/UI/Badge",
  component: Badge,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: [
        "primary",
        "secondary",
        "success",
        "warning",
        "danger",
        "info",
        "outline",
        "neutral",
      ],
    },
    size: { control: "select", options: ["sm", "md"] },
    dot: { control: "boolean" },
  },
  args: { children: "Метка", variant: "neutral", size: "md" },
} satisfies Meta<typeof Badge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Neutral: Story = {};
export const Primary: Story = { args: { variant: "primary", children: "Основной" } };
export const Success: Story = { args: { variant: "success", children: "Успешно" } };
export const Warning: Story = { args: { variant: "warning", children: "Внимание" } };
export const Danger: Story = { args: { variant: "danger", children: "Ошибка" } };
export const Info: Story = { args: { variant: "info", children: "Информация" } };
export const Outline: Story = { args: { variant: "outline", children: "Контур" } };

export const AllVariants: Story = {
  render: (args) => (
    <div className="flex flex-wrap gap-2">
      <Badge {...args} variant="primary">
        Основной
      </Badge>
      <Badge {...args} variant="secondary">
        Вторичный
      </Badge>
      <Badge {...args} variant="success">
        Успешно
      </Badge>
      <Badge {...args} variant="warning">
        Внимание
      </Badge>
      <Badge {...args} variant="danger">
        Ошибка
      </Badge>
      <Badge {...args} variant="info">
        Информация
      </Badge>
      <Badge {...args} variant="outline">
        Контур
      </Badge>
      <Badge {...args} variant="neutral">
        Нейтральный
      </Badge>
    </div>
  ),
  args: { children: undefined },
};

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex items-center gap-2">
      <Badge {...args} size="sm">
        Малый
      </Badge>
      <Badge {...args} size="md">
        Средний
      </Badge>
    </div>
  ),
  args: { children: undefined, variant: "primary" },
};

export const WithDot: Story = {
  args: { dot: true, variant: "success", children: "В сети" },
};

export const WithIcon: Story = {
  render: (args) => (
    <div className="flex gap-2">
      <Badge {...args} variant="success" icon={<Check />}>
        Готово
      </Badge>
      <Badge {...args} variant="warning" icon={<Star />}>
        Избранное
      </Badge>
    </div>
  ),
  args: { children: undefined },
};
