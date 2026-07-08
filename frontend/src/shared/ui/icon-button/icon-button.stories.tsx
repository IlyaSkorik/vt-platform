import type { Meta, StoryObj } from "@storybook/react-vite";
import { Bell, Heart, Trash2 } from "lucide-react";
import { IconButton } from "./icon-button";

const meta = {
  title: "Shared/UI/IconButton",
  component: IconButton,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "outline", "ghost", "danger", "success"],
    },
    size: { control: "select", options: ["xs", "sm", "md", "lg", "xl"] },
    disabled: { control: "boolean" },
    loading: { control: "boolean" },
  },
  args: { icon: <Bell />, "aria-label": "Уведомления", variant: "primary", size: "md" },
} satisfies Meta<typeof IconButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex items-center gap-3">
      <IconButton {...args} size="xs" />
      <IconButton {...args} size="sm" />
      <IconButton {...args} size="md" />
      <IconButton {...args} size="lg" />
      <IconButton {...args} size="xl" />
    </div>
  ),
};

export const Variants: Story = {
  render: (args) => (
    <div className="flex items-center gap-3">
      <IconButton {...args} variant="primary" icon={<Heart />} aria-label="Нравится" />
      <IconButton {...args} variant="outline" icon={<Bell />} aria-label="Уведомления" />
      <IconButton {...args} variant="ghost" icon={<Bell />} aria-label="Уведомления" />
      <IconButton {...args} variant="danger" icon={<Trash2 />} aria-label="Удалить" />
    </div>
  ),
};

export const Loading: Story = { args: { loading: true } };
export const Disabled: Story = { args: { disabled: true } };
