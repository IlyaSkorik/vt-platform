import type { Meta, StoryObj } from "@storybook/react-vite";
import { userEvent, within } from "storybook/test";
import { LoginForm } from "./login-form";
import {
  mockErrorFetch,
  mockPendingFetch,
  mockSuccessFetch,
  withAuthProviders,
} from "./story-utils";

const meta = {
  title: "Features/Auth/LoginForm",
  component: LoginForm,
  parameters: { layout: "centered" },
  decorators: [withAuthProviders],
  args: { onSuccess: () => undefined },
} satisfies Meta<typeof LoginForm>;

export default meta;

type Story = StoryObj<typeof meta>;

/** Empty form, ready for input. */
export const Default: Story = {
  beforeEach: () => {
    mockSuccessFetch();
  },
};

/** Submission in flight — the submit button shows its busy state. */
export const Loading: Story = {
  beforeEach: () => {
    mockPendingFetch();
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "user@example.com");
    await userEvent.type(canvas.getByLabelText("Пароль"), "password123");
    await userEvent.click(canvas.getByRole("button", { name: "Войти" }));
  },
};

/** Server rejected the credentials — a form-level error Alert renders. */
export const ServerError: Story = {
  beforeEach: () => {
    mockErrorFetch(401);
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Email"), "user@example.com");
    await userEvent.type(canvas.getByLabelText("Пароль"), "wrong-password");
    await userEvent.click(canvas.getByRole("button", { name: "Войти" }));
  },
};

/** Client validation errors shown after an empty submit. */
export const ValidationErrors: Story = {
  beforeEach: () => {
    mockSuccessFetch();
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Войти" }));
  },
};
