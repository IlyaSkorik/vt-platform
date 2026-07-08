import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Pagination } from "./pagination";

const meta = {
  title: "Shared/UI/Pagination",
  component: Pagination,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    page: { control: { type: "number", min: 1 } },
    pageCount: { control: { type: "number", min: 1 } },
    siblingCount: { control: { type: "number", min: 0 } },
  },
  args: { page: 1, siblingCount: 1, onPageChange: () => {} },
} satisfies Meta<typeof Pagination>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { pageCount: 10 },
  render: (args) => {
    const [page, setPage] = useState(args.page);
    return <Pagination {...args} page={page} onPageChange={setPage} />;
  },
};

export const ManyPages: Story = {
  args: { pageCount: 50, page: 8 },
  render: (args) => {
    const [page, setPage] = useState(args.page);
    return <Pagination {...args} page={page} onPageChange={setPage} />;
  },
};

export const FromTotal: Story = {
  args: { total: 137, pageSize: 10 },
  render: (args) => {
    const [page, setPage] = useState(1);
    return <Pagination {...args} page={page} onPageChange={setPage} />;
  },
};

export const FewPages: Story = {
  args: { pageCount: 3 },
  render: (args) => {
    const [page, setPage] = useState(1);
    return <Pagination {...args} page={page} onPageChange={setPage} />;
  },
};
