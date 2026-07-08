import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router";
import { NAVIGATION, ROUTES } from "@/shared/config";
import { TooltipProvider } from "@/shared/ui";
import { Sidebar } from "./sidebar";

/**
 * The Sidebar in isolation — the persistent desktop/tablet navigation column.
 * Shown both expanded and collapsed to the icon rail. In the rail, each item
 * exposes its label through an accessible tooltip on hover/focus.
 */
const meta = {
  title: "Shell/Sidebar",
  component: Sidebar,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/participants"]}>
        <TooltipProvider>
          <div className="flex h-svh">
            <Story />
          </div>
        </TooltipProvider>
      </MemoryRouter>
    ),
  ],
  args: {
    navigation: NAVIGATION,
    homeHref: ROUTES.dashboard,
    onToggleCollapsed: () => {},
  },
} satisfies Meta<typeof Sidebar>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Expanded: Story = {
  args: { collapsed: false },
};

export const Collapsed: Story = {
  args: { collapsed: true },
};
