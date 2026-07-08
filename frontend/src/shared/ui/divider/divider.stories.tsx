import type { Meta, StoryObj } from "@storybook/react-vite";
import { Divider } from "./divider";

const meta = {
  title: "Shared/UI/Divider",
  component: Divider,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    orientation: { control: "inline-radio", options: ["horizontal", "vertical"] },
    decorative: { control: "boolean" },
    label: { control: "text" },
  },
} satisfies Meta<typeof Divider>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Horizontal: Story = {
  render: (args) => (
    <div className="w-64">
      <p className="text-sm text-foreground">Верхний блок</p>
      <Divider {...args} className="my-3" />
      <p className="text-sm text-foreground">Нижний блок</p>
    </div>
  ),
};

export const Vertical: Story = {
  render: (args) => (
    <div className="flex h-10 items-center gap-3">
      <span className="text-sm text-foreground">Слева</span>
      <Divider {...args} orientation="vertical" />
      <span className="text-sm text-foreground">Справа</span>
    </div>
  ),
};

export const WithLabel: Story = {
  args: { label: "или" },
  render: (args) => (
    <div className="w-64">
      <Divider {...args} />
    </div>
  ),
};
