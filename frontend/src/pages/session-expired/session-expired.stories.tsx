import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router";
import { SessionExpiredPage } from "./index";

const meta = {
  title: "Pages/Auth/SessionExpired",
  component: SessionExpiredPage,
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
} satisfies Meta<typeof SessionExpiredPage>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
