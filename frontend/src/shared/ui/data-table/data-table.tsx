import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { useState } from "react";
import { cn } from "@/shared/lib/cn";
import type { DataTableProps } from "./types";

/**
 * DataTable — a headless, generic table built on TanStack Table v8. Accepts
 * `columns` + `data` for any row shape `TData`, renders a token-styled
 * semantic table, and handles client-side sorting UI, loading and empty
 * states. Carries no domain logic (WCAG 2.1 AA).
 */
export function DataTable<TData>({
  columns,
  data,
  loading = false,
  emptyContent,
  enableSorting = true,
  className,
  containerClassName,
  ref,
  ...props
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableSorting,
  });

  const rows = table.getRowModel().rows;
  const columnCount = table.getAllLeafColumns().length;
  const hasRows = rows.length > 0;

  return (
    <div
      className={cn(
        "relative w-full overflow-x-auto rounded-lg border border-border bg-card",
        containerClassName,
      )}
    >
      <table
        ref={ref}
        data-slot="data-table"
        className={cn("w-full caption-bottom text-sm text-card-foreground", className)}
        {...props}
      >
        <thead className="border-b border-border bg-muted/50 text-muted-foreground">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sortDir = header.column.getIsSorted();
                return (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    aria-sort={
                      sortDir === "asc"
                        ? "ascending"
                        : sortDir === "desc"
                          ? "descending"
                          : undefined
                    }
                    className="h-10 px-3 text-left align-middle font-medium whitespace-nowrap"
                  >
                    {header.isPlaceholder ? null : canSort ? (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className="inline-flex items-center gap-1.5 rounded-md outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 [&_svg]:size-3.5"
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sortDir === "asc" ? (
                          <ArrowUp aria-hidden="true" />
                        ) : sortDir === "desc" ? (
                          <ArrowDown aria-hidden="true" />
                        ) : (
                          <ChevronsUpDown aria-hidden="true" className="opacity-50" />
                        )}
                      </button>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columnCount} className="h-24 p-0">
                <div
                  role="status"
                  aria-live="polite"
                  aria-label="Загрузка"
                  className="flex w-full items-center justify-center py-8 text-muted-foreground"
                >
                  <span
                    aria-hidden="true"
                    className="size-6 animate-spin rounded-full border-2 border-muted border-t-primary"
                  />
                  <span className="sr-only">Загрузка</span>
                </div>
              </td>
            </tr>
          ) : hasRows ? (
            rows.map((row) => (
              <tr
                key={row.id}
                data-state={row.getIsSelected() ? "selected" : undefined}
                className="border-b border-border transition-colors last:border-0 hover:bg-muted/50 data-[state=selected]:bg-muted"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 align-middle">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columnCount} className="h-24 p-0">
                {emptyContent ?? (
                  <div className="flex w-full items-center justify-center py-8 text-sm text-muted-foreground">
                    Нет данных
                  </div>
                )}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export type { ColumnDef };
