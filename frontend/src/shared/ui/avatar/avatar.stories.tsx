import type { Meta, StoryObj } from "@storybook/react-vite";
import { Avatar } from "./avatar";

const meta = {
  title: "Shared/UI/Avatar",
  component: Avatar,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["xs", "sm", "md", "lg", "xl"] },
    src: { control: "text" },
  },
  args: {
    src: "https://i.pravatar.cc/150?img=12",
    alt: "Портрет пользователя",
    fallback: "ИП",
    size: "md",
  },
} satisfies Meta<typeof Avatar>;

export default meta;

type Story = StoryObj<typeof meta>;

export const WithImage: Story = {};

export const Fallback: Story = {
  render: () => <Avatar fallback="АБ" size="md" />,
};

export const BrokenImage: Story = {
  args: { src: "https://example.com/does-not-exist.jpg", fallback: "ВГ" },
};

export const AllSizes: Story = {
  render: (args) => (
    <div className="flex items-center gap-3">
      <Avatar {...args} size="xs" />
      <Avatar {...args} size="sm" />
      <Avatar {...args} size="md" />
      <Avatar {...args} size="lg" />
      <Avatar {...args} size="xl" />
    </div>
  ),
};

export const Group: Story = {
  render: (args) => (
    <div className="flex -space-x-2">
      <Avatar {...args} fallback="АА" className="ring-2 ring-background" />
      <Avatar fallback="ББ" size="md" className="ring-2 ring-background" />
      <Avatar fallback="ВВ" size="md" className="ring-2 ring-background" />
    </div>
  ),
};
