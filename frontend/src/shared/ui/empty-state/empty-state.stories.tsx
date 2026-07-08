import type { Meta, StoryObj } from "@storybook/react-vite";
import { Search } from "lucide-react";
import { EmptyState } from "./empty-state";

const meta = {
  title: "Shared/UI/EmptyState",
  component: EmptyState,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    title: { control: "text" },
    description: { control: "text" },
  },
  args: {
    title: "Нет данных",
    description: "Здесь пока ничего нет.",
  },
} satisfies Meta<typeof EmptyState>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutDescription: Story = {
  args: { title: "Список пуст", description: undefined },
};

export const CustomIcon: Story = {
  args: {
    icon: <Search />,
    title: "Ничего не найдено",
    description: "Попробуйте изменить условия поиска.",
  },
};

export const WithAction: Story = {
  args: {
    title: "Нет участников",
    description: "Добавьте первого участника, чтобы начать работу.",
    action: (
      <button
        type="button"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-elevation-1 hover:bg-primary/90"
      >
        Добавить участника
      </button>
    ),
  },
};
