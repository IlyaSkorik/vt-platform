import type { Meta, StoryObj } from "@storybook/react-vite";
import { MOCK_ACTIVITY } from "../../model/mock-data";
import { withCardWidth } from "../../story-utils";
import { ActivityTimelineView } from "./activity-timeline";

const meta = {
  title: "Dashboard/ActivityTimeline",
  component: ActivityTimelineView,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [withCardWidth],
  args: {
    status: "success",
    events: MOCK_ACTIVITY,
  },
} satisfies Meta<typeof ActivityTimelineView>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {};

export const Loading: Story = {
  args: { status: "loading", events: [] },
};

export const Empty: Story = {
  args: { status: "empty", events: [] },
};

export const Errored: Story = {
  args: { status: "error", events: [], onRetry: () => undefined },
};
