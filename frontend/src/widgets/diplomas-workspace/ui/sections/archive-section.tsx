import { Archive } from "lucide-react";
import { useMemo } from "react";
import { type ColumnDef, DataTable, EmptyState } from "@/shared/ui";

/**
 * A generation-archive row. No backend yet — the table renders empty for now,
 * but the columns fix the future shape (date, competition, count, user, download).
 */
interface ArchiveEntry {
  id: string;
  generatedAt: string;
  competition: string;
  count: number;
  user: string;
}

export function ArchiveSection(): React.JSX.Element {
  const columns: ColumnDef<ArchiveEntry>[] = useMemo(
    () => [
      { accessorKey: "generatedAt", header: "Дата генерации" },
      { accessorKey: "competition", header: "Конкурс" },
      { accessorKey: "count", header: "Дипломов" },
      { accessorKey: "user", header: "Пользователь" },
      { id: "download", header: "", cell: () => null },
    ],
    [],
  );

  return (
    <DataTable
      columns={columns}
      data={[]}
      emptyContent={
        <EmptyState
          icon={<Archive className="size-6" aria-hidden="true" />}
          title="Архив пуст"
          description="Здесь будет история генераций: дата, конкурс, количество дипломов, пользователь и повторное скачивание."
        />
      }
    />
  );
}
