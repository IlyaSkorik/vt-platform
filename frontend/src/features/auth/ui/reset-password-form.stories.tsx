import type { Meta, StoryObj } from "@storybook/react-vite";
import { userEvent, within } from "storybook/test";
import { ResetPasswordForm } from "./reset-password-form";
import {
  mockErrorFetch,
  mockPendingFetch,
  mockSuccessFetch,
  withAuthProviders,
} from "./story-utils";

const meta = {
  title: "Features/Auth/ResetPasswordForm",
  component: ResetPasswordForm,
  parameters: { layout: "centered" },
  decorators: [withAuthProviders],
  args: { token: "story-token", onSuccess: () => undefined },
} satisfies Meta<typeof ResetPasswordForm>;

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
    await userEvent.type(canvas.getByLabelText("Новый пароль"), "SuperSecret123!");
    await userEvent.type(canvas.getByLabelText("Подтверждение пароля"), "SuperSecret123!");
    await userEvent.click(canvas.getByRole("button", { name: "Сохранить пароль" }));
  },
};

/** Expired reset token (410) — a form-level error Alert renders. */
export const ServerError: Story = {
  beforeEach: () => {
    mockErrorFetch(410);
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Новый пароль"), "SuperSecret123!");
    await userEvent.type(canvas.getByLabelText("Подтверждение пароля"), "SuperSecret123!");
    await userEvent.click(canvas.getByRole("button", { name: "Сохранить пароль" }));
  },
};

/** Client validation: policy failure and mismatched confirmation. */
export const ValidationErrors: Story = {
  beforeEach: () => {
    mockSuccessFetch();
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Новый пароль"), "short");
    await userEvent.type(canvas.getByLabelText("Подтверждение пароля"), "different");
    await userEvent.click(canvas.getByRole("button", { name: "Сохранить пароль" }));
  },
};
