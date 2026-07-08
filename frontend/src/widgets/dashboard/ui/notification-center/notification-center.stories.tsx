import type { Meta, StoryObj } from "@storybook/react-vite";
import { MOCK_NOTIFICATIONS } from "../../model/mock-data";
import { withCardWidth } from "../../story-utils";
import { NotificationCenterView } from "./notification-center";

const meta = {
  title: "Dashboard/NotificationCenter",
  component: NotificationCenterView,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [withCardWidth],
  args: {
    status: "success",
    notifications: MOCK_NOTIFICATIONS,
  },
} satisfies Meta<typeof NotificationCenterView>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {};

export const AllRead: Story = {
  args: {
    notifications: MOCK_NOTIFICATIONS.map((n) => ({ ...n, read: true })),
  },
};

export const Loading: Story = {
  args: { status: "loading", notifications: [] },
};

export const Empty: Story = {
  args: { status: "empty", notifications: [] },
};

export const Errored: Story = {
  args: { status: "error", notifications: [], onRetry: () => undefined },
};
