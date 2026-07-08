import type { Meta, StoryObj } from "@storybook/react-vite";
import { MOCK_APPLICATIONS } from "../../model/mock-data";
import { withCardWidth, withDashboardProviders } from "../../story-utils";
import { RecentApplicationsView } from "./recent-applications";

const meta = {
  title: "Dashboard/RecentApplications",
  component: RecentApplicationsView,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [withCardWidth, withDashboardProviders],
  args: {
    status: "success",
    applications: MOCK_APPLICATIONS,
  },
} satisfies Meta<typeof RecentApplicationsView>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {};

export const Loading: Story = {
  args: { status: "loading", applications: [] },
};

export const Empty: Story = {
  args: { status: "empty", applications: [] },
};

export const Errored: Story = {
  args: { status: "error", applications: [], onRetry: () => undefined },
};
