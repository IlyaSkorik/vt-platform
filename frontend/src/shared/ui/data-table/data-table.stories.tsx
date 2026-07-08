import type { Meta, StoryObj } from "@storybook/react-vite";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "./data-table";

interface Participant {
  id: number;
  name: string;
  role: string;
  score: number;
}

const columns: ColumnDef<Participant, unknown>[] = [
  { accessorKey: "name", header: "Имя" },
  { accessorKey: "role", header: "Роль" },
  { accessorKey: "score", header: "Баллы" },
];

const data: Participant[] = [
  { id: 1, name: "Анна Иванова", role: "Наставник", score: 92 },
  { id: 2, name: "Борис Петров", role: "Участник", score: 78 },
  { id: 3, name: "Виктория Смирнова", role: "Участник", score: 85 },
  { id: 4, name: "Григорий Кузнецов", role: "Эксперт", score: 64 },
];

const meta = {
  title: "Shared/UI/DataTable",
  component: DataTable<Participant>,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  args: { columns, data },
} satisfies Meta<typeof DataTable<Participant>>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Loading: Story = { args: { loading: true, data: [] } };

export const Empty: Story = { args: { data: [] } };

export const CustomEmpty: Story = {
  args: {
    data: [],
    emptyContent: (
      <div className="flex flex-col items-center gap-1 py-8 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Участников пока нет</span>
        <span>Добавьте первого участника, чтобы увидеть таблицу.</span>
      </div>
    ),
  },
};

export const SortingDisabled: Story = { args: { enableSorting: false } };
