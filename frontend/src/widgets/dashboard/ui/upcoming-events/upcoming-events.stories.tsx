import type { Meta, StoryObj } from "@storybook/react-vite";
import { MOCK_EVENTS } from "../../model/mock-data";
import { withCardWidth } from "../../story-utils";
import { UpcomingEventsView } from "./upcoming-events";

const meta = {
  title: "Dashboard/UpcomingEvents",
  component: UpcomingEventsView,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [withCardWidth],
  args: {
    status: "success",
    events: MOCK_EVENTS,
  },
} satisfies Meta<typeof UpcomingEventsView>;

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
