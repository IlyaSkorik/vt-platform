import type { Meta, StoryObj } from "@storybook/react-vite";
import { Users } from "lucide-react";
import { StatCard } from "./stat-card";

const meta = {
  title: "Dashboard/StatCard",
  component: StatCard,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="w-72">
        <Story />
      </div>
    ),
  ],
  args: {
    label: "Участники",
    icon: Users,
    tone: "primary",
    status: "success",
    value: "1 284",
    delta: "+12,5 %",
    trend: "up",
  },
} satisfies Meta<typeof StatCard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {};

export const Loading: Story = {
  args: { status: "loading" },
};

export const Empty: Story = {
  args: { status: "empty", emptyLabel: "Нет данных" },
};

export const Errored: Story = {
  args: { status: "error", onRetry: () => undefined },
};

export const DownwardTrend: Story = {
  args: { tone: "warning", value: "3 472", delta: "−3,2 %", trend: "down" },
};
