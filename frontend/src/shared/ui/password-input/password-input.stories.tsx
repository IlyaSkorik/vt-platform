import type { Meta, StoryObj } from "@storybook/react-vite";
import { PasswordInput } from "./password-input";

const meta = {
  title: "Shared/UI/PasswordInput",
  component: PasswordInput,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { label: "Пароль", placeholder: "••••••••" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof PasswordInput>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithDescription: Story = {
  args: { description: "Минимум 8 символов, буквы и цифры." },
};
export const WithError: Story = {
  args: { error: "Пароль слишком короткий.", defaultValue: "123" },
};
export const Disabled: Story = { args: { disabled: true, defaultValue: "secret" } };
