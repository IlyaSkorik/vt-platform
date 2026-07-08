import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router";
import { UnauthorizedPage } from "./index";

const meta = {
  title: "Pages/Auth/Unauthorized",
  component: UnauthorizedPage,
  parameters: { layout: "centered" },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div className="w-full max-w-sm">
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
} satisfies Meta<typeof UnauthorizedPage>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
