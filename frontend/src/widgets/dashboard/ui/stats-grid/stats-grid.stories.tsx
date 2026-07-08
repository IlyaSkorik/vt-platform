import type { Meta, StoryObj } from "@storybook/react-vite";
import { withDashboardProviders } from "../../story-utils";
import { StatsGrid } from "./stats-grid";

/**
 * StatsGrid is connected to `useDashboardStats`; the decorator provides a
 * QueryClient so the mock resolves. Individual four-state coverage lives in the
 * `StatCard` stories (the pure tile the grid renders).
 */
const meta = {
  title: "Dashboard/StatsGrid",
  component: StatsGrid,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  decorators: [withDashboardProviders],
} satisfies Meta<typeof StatsGrid>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
