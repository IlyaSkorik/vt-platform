import type { Meta, StoryObj } from "@storybook/react-vite";
import { Checkbox } from "./checkbox";

const meta = {
  title: "Shared/UI/Checkbox",
  component: Checkbox,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md"] },
    disabled: { control: "boolean" },
    required: { control: "boolean" },
  },
  args: { label: "Принимаю условия" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Checkbox>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Checked: Story = { args: { defaultChecked: true } };
export const Indeterminate: Story = {
  args: { checked: "indeterminate", label: "Выбрано частично" },
};
export const WithDescription: Story = {
  args: { description: "Мы отправим подтверждение на вашу почту." },
};
export const WithError: Story = { args: { error: "Необходимо согласие." } };
export const Required: Story = { args: { required: true, label: "Обязательное согласие" } };
export const Disabled: Story = { args: { disabled: true, label: "Недоступно" } };
export const DisabledChecked: Story = {
  args: { disabled: true, defaultChecked: true, label: "Недоступно (выбрано)" },
};

export const Sizes: Story = {
  render: (args) => (
    <div className="flex flex-col gap-3">
      <Checkbox {...args} size="sm" label="Маленький (sm)" />
      <Checkbox {...args} size="md" label="Средний (md)" />
    </div>
  ),
  args: { label: undefined },
};
