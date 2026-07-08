import type { Meta, StoryObj } from "@storybook/react-vite";
import { Skeleton } from "./skeleton";

const meta = {
  title: "Shared/UI/Skeleton",
  component: Skeleton,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "inline-radio", options: ["text", "circle", "rect"] },
  },
} satisfies Meta<typeof Skeleton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Text: Story = {
  args: { variant: "text" },
  render: (args) => <Skeleton {...args} className="w-64" />,
};

export const Circle: Story = {
  args: { variant: "circle" },
  render: (args) => <Skeleton {...args} className="size-12" />,
};

export const Rect: Story = {
  args: { variant: "rect" },
  render: (args) => <Skeleton {...args} className="h-24 w-64" />,
};

export const CardPlaceholder: Story = {
  render: () => (
    <div className="flex w-72 flex-col gap-4 rounded-lg border bg-card p-4">
      <div className="flex items-center gap-3">
        <Skeleton variant="circle" className="size-10" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton variant="text" className="w-2/3" />
          <Skeleton variant="text" className="w-1/3" />
        </div>
      </div>
      <Skeleton variant="rect" className="h-24 w-full" />
      <Skeleton variant="text" className="w-full" />
      <Skeleton variant="text" className="w-5/6" />
    </div>
  ),
};
