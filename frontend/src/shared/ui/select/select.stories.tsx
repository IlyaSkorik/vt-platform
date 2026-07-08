import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectRoot,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "./select";

const fruits = [
  { value: "apple", label: "Яблоко" },
  { value: "banana", label: "Банан" },
  { value: "cherry", label: "Вишня" },
  { value: "grape", label: "Виноград", disabled: true },
];

const grouped = [
  {
    label: "Фрукты",
    options: [
      { value: "apple", label: "Яблоко" },
      { value: "banana", label: "Банан" },
    ],
  },
  {
    label: "Овощи",
    options: [
      { value: "carrot", label: "Морковь" },
      { value: "potato", label: "Картофель" },
    ],
  },
];

const meta = {
  title: "Shared/UI/Select",
  component: Select,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md"] },
    disabled: { control: "boolean" },
    required: { control: "boolean" },
  },
  args: { label: "Продукт", placeholder: "Выберите продукт", options: fruits },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Select>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithDefaultValue: Story = { args: { defaultValue: "banana" } };
export const Grouped: Story = { args: { options: grouped } };
export const WithDescription: Story = {
  args: { description: "Свежие продукты с доставкой." },
};
export const WithError: Story = { args: { error: "Необходимо выбрать продукт." } };
export const Required: Story = { args: { required: true } };
export const Disabled: Story = { args: { disabled: true } };
export const Small: Story = { args: { size: "sm" } };

export const Composable: Story = {
  name: "Composable parts",
  render: () => (
    <SelectRoot>
      <SelectTrigger aria-label="Продукт">
        <SelectValue placeholder="Выберите продукт" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>Фрукты</SelectLabel>
          <SelectItem value="apple">Яблоко</SelectItem>
          <SelectItem value="banana">Банан</SelectItem>
        </SelectGroup>
        <SelectSeparator />
        <SelectGroup>
          <SelectLabel>Овощи</SelectLabel>
          <SelectItem value="carrot">Морковь</SelectItem>
          <SelectItem value="potato">Картофель</SelectItem>
        </SelectGroup>
      </SelectContent>
    </SelectRoot>
  ),
};
