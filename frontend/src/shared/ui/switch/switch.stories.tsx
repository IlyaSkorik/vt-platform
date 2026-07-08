import type { Meta, StoryObj } from "@storybook/react-vite";
import { Switch } from "./switch";

const meta = {
  title: "Shared/UI/Switch",
  component: Switch,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md"] },
    disabled: { control: "boolean" },
  },
  args: { label: "Включить уведомления" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Switch>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Checked: Story = { args: { defaultChecked: true } };
export const WithDescription: Story = {
  args: { description: "Присылать письма о важных событиях." },
};
export const Disabled: Story = { args: { disabled: true, label: "Недоступно" } };
export const DisabledChecked: Story = {
  args: { disabled: true, defaultChecked: true, label: "Недоступно (включено)" },
};
export const WithoutLabel: Story = { args: { label: undefined, "aria-label": "Переключатель" } };

export const Sizes: Story = {
  render: (args) => (
    <div className="flex flex-col gap-3">
      <Switch {...args} size="sm" label="Маленький (sm)" />
      <Switch {...args} size="md" label="Средний (md)" />
    </div>
  ),
  args: { label: undefined },
};
