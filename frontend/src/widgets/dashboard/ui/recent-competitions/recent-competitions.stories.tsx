import type { Meta, StoryObj } from "@storybook/react-vite";
import { MOCK_COMPETITIONS } from "../../model/mock-data";
import { withCardWidth, withDashboardProviders } from "../../story-utils";
import { RecentCompetitionsView } from "./recent-competitions";

const meta = {
  title: "Dashboard/RecentCompetitions",
  component: RecentCompetitionsView,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [withCardWidth, withDashboardProviders],
  args: {
    status: "success",
    competitions: MOCK_COMPETITIONS,
  },
} satisfies Meta<typeof RecentCompetitionsView>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {};

export const Loading: Story = {
  args: { status: "loading", competitions: [] },
};

export const Empty: Story = {
  args: { status: "empty", competitions: [] },
};

export const Errored: Story = {
  args: { status: "error", competitions: [], onRetry: () => undefined },
};
