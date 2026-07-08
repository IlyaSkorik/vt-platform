import type { Meta, StoryObj } from "@storybook/react-vite";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { Button } from "./button";

const meta = {
  title: "Shared/UI/Button",
  component: Button,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["primary", "secondary", "outline", "ghost", "danger", "success"],
    },
    size: { control: "select", options: ["xs", "sm", "md", "lg", "xl"] },
    disabled: { control: "boolean" },
    loading: { control: "boolean" },
    iconOnly: { control: "boolean" },
  },
  args: { children: "Кнопка", variant: "primary", size: "md" },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Primary: Story = {};
export const Secondary: Story = { args: { variant: "secondary", children: "Вторичная" } };
export const Outline: Story = { args: { variant: "outline", children: "Контурная" } };
export const Ghost: Story = { args: { variant: "ghost", children: "Прозрачная" } };
export const Danger: Story = { args: { variant: "danger", children: "Удалить" } };
export const Success: Story = { args: { variant: "success", children: "Готово" } };

export const AllVariants: Story = {
  render: (args) => (
    <div className="flex flex-wrap gap-3">
      <Button {...args} variant="primary">
        Primary
      </Button>
      <Button {...args} variant="secondary">
        Secondary
      </Button>
      <Button {...args} variant="outline">
        Outline
      </Button>
      <Button {...args} variant="ghost">
        Ghost
      </Button>
      <Button {...args} variant="danger">
        Danger
      </Button>
      <Button {...args} variant="success">
        Success
      </Button>
    </div>
  ),
  args: { children: undefined },
};

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex flex-wrap items-center gap-3">
      <Button {...args} size="xs">
        XS
      </Button>
      <Button {...args} size="sm">
        SM
      </Button>
      <Button {...args} size="md">
        MD
      </Button>
      <Button {...args} size="lg">
        LG
      </Button>
      <Button {...args} size="xl">
        XL
      </Button>
    </div>
  ),
  args: { children: undefined },
};

export const WithIcons: Story = {
  render: (args) => (
    <div className="flex flex-wrap gap-3">
      <Button {...args} leftIcon={<Plus />}>
        Добавить
      </Button>
      <Button {...args} rightIcon={<ArrowRight />}>
        Далее
      </Button>
    </div>
  ),
  args: { children: undefined },
};

export const Loading: Story = { args: { loading: true, children: "Сохранение" } };
export const Disabled: Story = { args: { disabled: true, children: "Недоступна" } };

export const IconOnly: Story = {
  args: { iconOnly: true, children: <Trash2 />, variant: "danger", "aria-label": "Удалить" },
};

export const AsChildLink: Story = {
  name: "As child (anchor)",
  args: { asChild: true, children: <a href="https://example.com">Перейти</a> },
};
