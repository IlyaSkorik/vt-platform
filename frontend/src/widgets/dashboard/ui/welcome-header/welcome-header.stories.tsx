import type { Meta, StoryObj } from "@storybook/react-vite";
import { WelcomeHeader } from "./welcome-header";

const meta = {
  title: "Dashboard/WelcomeHeader",
  component: WelcomeHeader,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  args: {
    userName: "Мария",
    now: new Date("2026-07-08T10:30:00"),
  },
} satisfies Meta<typeof WelcomeHeader>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Morning: Story = {
  args: { now: new Date("2026-07-08T09:00:00") },
};

export const Afternoon: Story = {
  args: { now: new Date("2026-07-08T14:00:00") },
};

export const Evening: Story = {
  args: { now: new Date("2026-07-08T20:00:00") },
};

export const Loading: Story = {
  args: { userName: undefined },
};
