import type { Meta, StoryObj } from "@storybook/react-vite";
import { withDashboardProviders } from "../../story-utils";
import { QuickActions } from "./quick-actions";

const meta = {
  title: "Dashboard/QuickActions",
  component: QuickActions,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  decorators: [withDashboardProviders],
} satisfies Meta<typeof QuickActions>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
