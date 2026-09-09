import type { Meta, StoryObj } from "@storybook/react-vite";
import { userEvent, within } from "storybook/test";
import { RegisterForm } from "./register-form";
import {
  mockErrorFetch,
  mockPendingFetch,
  mockSuccessFetch,
  withAuthProviders,
} from "./story-utils";

const meta = {
  title: "Features/Auth/RegisterForm",
  component: RegisterForm,
  parameters: { layout: "centered" },
  decorators: [withAuthProviders],
  args: { onSuccess: () => undefined },
} satisfies Meta<typeof RegisterForm>;

export default meta;

type Story = StoryObj<typeof meta>;

async function fillValidForm(canvasElement: HTMLElement): Promise<void> {
  const canvas = within(canvasElement);
  await userEvent.type(canvas.getByLabelText("Имя"), "Ирина");
  await userEvent.type(canvas.getByLabelText("Фамилия"), "Смирнова");
  await userEvent.type(canvas.getByLabelText("Email"), "irina@example.com");
  await userEvent.type(canvas.getByLabelText("Пароль"), "SuperSecret123!");
  await userEvent.type(canvas.getByLabelText("Подтверждение пароля"), "SuperSecret123!");
  await userEvent.click(canvas.getByRole("checkbox"));
}

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
    await fillValidForm(canvasElement);
    await userEvent.click(
      within(canvasElement).getByRole("button", { name: "Зарегистрироваться" }),
    );
  },
};

/** Email already in use — server 409 surfaced as a form-level Alert. */
export const ServerError: Story = {
  beforeEach: () => {
    mockErrorFetch(409);
  },
  play: async ({ canvasElement }) => {
    await fillValidForm(canvasElement);
    await userEvent.click(
      within(canvasElement).getByRole("button", { name: "Зарегистрироваться" }),
    );
  },
};

/** Client validation: required fields, password policy, terms acceptance. */
export const ValidationErrors: Story = {
  beforeEach: () => {
    mockSuccessFetch();
  },
  play: async ({ canvasElement }) => {
    await userEvent.click(
      within(canvasElement).getByRole("button", { name: "Зарегистрироваться" }),
    );
  },
};
