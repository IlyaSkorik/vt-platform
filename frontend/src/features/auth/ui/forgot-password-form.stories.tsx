import type { Meta, StoryObj } from "@storybook/react-vite";
import { userEvent, within } from "storybook/test";
import { ForgotPasswordForm } from "./forgot-password-form";
import {
  mockErrorFetch,
  mockPendingFetch,
  mockSuccessFetch,
  withAuthProviders,
} from "./story-utils";

const meta = {
  title: "Features/Auth/ForgotPasswordForm",
  component: ForgotPasswordForm,
  parameters: { layout: "centered" },
  decorators: [withAuthProviders],
  args: { onSuccess: () => undefined },
} satisfies Meta<typeof ForgotPasswordForm>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  beforeEach: () => {
    mockSuccessFetch();
  },
};

export const Loading: Story = {
  beforeEach: () => {
    mockPendingFetch();
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "user@example.com");
    await userEvent.click(canvas.getByRole("button", { name: "Отправить ссылку" }));
  },
};

/** Rate limited (429) — a form-level error Alert renders. */
export const ServerError: Story = {
  beforeEach: () => {
    mockErrorFetch(429);
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "user@example.com");
    await userEvent.click(canvas.getByRole("button", { name: "Отправить ссылку" }));
  },
};
