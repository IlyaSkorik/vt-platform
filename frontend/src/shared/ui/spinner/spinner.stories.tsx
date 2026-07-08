import type { Meta, StoryObj } from "@storybook/react-vite";
import { Spinner } from "./spinner";

const meta = {
  title: "Shared/UI/Spinner",
  component: Spinner,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["xs", "sm", "md", "lg", "xl"] },
    label: { control: "text" },
  },
  args: { size: "md", label: "Загрузка" },
} satisfies Meta<typeof Spinner>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex items-center gap-4">
      <Spinner {...args} size="xs" />
      <Spinner {...args} size="sm" />
      <Spinner {...args} size="md" />
      <Spinner {...args} size="lg" />
      <Spinner {...args} size="xl" />
    </div>
  ),
};

export const OnColoredSurface: Story = {
  render: (args) => (
    <div className="flex items-center gap-2 rounded-md bg-primary p-4 text-primary-foreground">
      <Spinner {...args} className="text-primary-foreground" />
      <span className="text-sm">Загрузка данных</span>
    </div>
  ),
};
