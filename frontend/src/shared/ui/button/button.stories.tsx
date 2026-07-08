import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";

const meta = {
  title: "Shared/UI/Button",
  component: Button,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "destructive", "outline", "secondary", "ghost", "link"],
    },
    size: {
      control: "select",
      options: ["default", "sm", "lg", "icon"],
    },
    disabled: { control: "boolean" },
  },
  args: {
    children: "Кнопка",
    variant: "default",
    size: "default",
  },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Secondary: Story = {
  args: { variant: "secondary", children: "Вторичная" },
};

export const Destructive: Story = {
  args: { variant: "destructive", children: "Удалить" },
};

export const Outline: Story = {
  args: { variant: "outline", children: "Контурная" },
};

export const Ghost: Story = {
  args: { variant: "ghost", children: "Прозрачная" },
};

export const Link: Story = {
  args: { variant: "link", children: "Ссылка" },
};

export const Disabled: Story = {
  args: { disabled: true, children: "Недоступна" },
};

export const AsChildLink: Story = {
  name: "As child (anchor)",
  args: {
    asChild: true,
    children: <a href="https://example.com">Перейти</a>,
  },
};
