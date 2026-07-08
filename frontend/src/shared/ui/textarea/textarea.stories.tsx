import type { Meta, StoryObj } from "@storybook/react-vite";
import { Textarea } from "./textarea";

const meta = {
  title: "Shared/UI/Textarea",
  component: Textarea,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: { disabled: { control: "boolean" }, readOnly: { control: "boolean" } },
  args: { label: "Комментарий", placeholder: "Поделитесь мыслями…" },
  decorators: [
    (Story) => (
      <div className="w-96">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Textarea>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithDescription: Story = { args: { description: "Не более 500 символов." } };
export const WithError: Story = { args: { error: "Поле обязательно для заполнения." } };
export const WithSuccess: Story = {
  args: { success: "Выглядит хорошо.", defaultValue: "Отлично!" },
};
export const Disabled: Story = { args: { disabled: true, defaultValue: "Недоступно" } };
export const ReadOnly: Story = { args: { readOnly: true, defaultValue: "Только для чтения" } };
