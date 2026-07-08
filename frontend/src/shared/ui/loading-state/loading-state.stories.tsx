import type { Meta, StoryObj } from "@storybook/react-vite";
import { LoadingState } from "./loading-state";

const meta = {
  title: "Shared/UI/LoadingState",
  component: LoadingState,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md", "lg"] },
    label: { control: "text" },
    srLabel: { control: "text" },
  },
  args: { size: "md" },
} satisfies Meta<typeof LoadingState>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithLabel: Story = { args: { label: "Загружаем данные…" } };

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex items-center gap-10">
      <LoadingState {...args} size="sm" label="Малый" />
      <LoadingState {...args} size="md" label="Средний" />
      <LoadingState {...args} size="lg" label="Большой" />
    </div>
  ),
};

export const InCard: Story = {
  render: (args) => (
    <div className="w-80 rounded-lg border border-border bg-card shadow-elevation-1">
      <LoadingState {...args} label="Подождите…" />
    </div>
  ),
};
