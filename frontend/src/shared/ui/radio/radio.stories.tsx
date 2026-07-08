import type { Meta, StoryObj } from "@storybook/react-vite";
import { Radio, RadioGroup } from "./radio";

const meta = {
  title: "Shared/UI/RadioGroup",
  component: RadioGroup,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md"] },
    orientation: { control: "select", options: ["vertical", "horizontal"] },
    disabled: { control: "boolean" },
  },
  args: { label: "Тарифный план" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof RadioGroup>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { defaultValue: "free" },
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Бесплатный" />
      <Radio value="pro" label="Профессиональный" />
      <Radio value="team" label="Командный" />
    </RadioGroup>
  ),
};

export const WithDescriptions: Story = {
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Бесплатный" description="Для личных проектов." />
      <Radio value="pro" label="Профессиональный" description="Расширенные лимиты и поддержка." />
      <Radio value="team" label="Командный" description="Совместная работа до 20 человек." />
    </RadioGroup>
  ),
};

export const Horizontal: Story = {
  args: { orientation: "horizontal" },
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Да" />
      <Radio value="pro" label="Нет" />
      <Radio value="team" label="Не знаю" />
    </RadioGroup>
  ),
};

export const WithError: Story = {
  args: { error: "Выберите один из вариантов." },
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Бесплатный" />
      <Radio value="pro" label="Профессиональный" />
    </RadioGroup>
  ),
};

export const Disabled: Story = {
  args: { disabled: true },
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Бесплатный" />
      <Radio value="pro" label="Профессиональный" />
    </RadioGroup>
  ),
};

export const Small: Story = {
  args: { size: "sm" },
  render: (args) => (
    <RadioGroup {...args}>
      <Radio value="free" label="Бесплатный" />
      <Radio value="pro" label="Профессиональный" />
    </RadioGroup>
  ),
};
