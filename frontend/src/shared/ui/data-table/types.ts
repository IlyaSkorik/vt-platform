import type { ColumnDef } from "@tanstack/react-table";
import type * as React from "react";

export interface DataTableProps<TData>
  extends Omit<React.HTMLAttributes<HTMLTableElement>, "children"> {
  /** Column definitions (headless — no domain assumptions). */
  columns: ColumnDef<TData, unknown>[];
  /** Row data. */
  data: TData[];
  /** Show a loading indicator overlaying the body. */
  loading?: boolean;
  /** Node rendered when there are no rows. Falls back to a default message. */
  emptyContent?: React.ReactNode;
  /** Enable client-side sorting UI. Defaults to true. */
  enableSorting?: boolean;
  /** Wrapper element className (the bordered container). */
  containerClassName?: string;
  /** Ref forwarded to the underlying `<table>` element. */
  ref?: React.Ref<HTMLTableElement>;
}
