import type * as React from "react";

export interface PaginationProps extends Omit<React.HTMLAttributes<HTMLElement>, "onChange"> {
  /** Current 1-based page. */
  page: number;
  /** Total number of pages. Provide this or `total` + `pageSize`. */
  pageCount?: number;
  /** Total item count, used with `pageSize` to derive `pageCount`. */
  total?: number;
  /** Items per page, used with `total` to derive `pageCount`. */
  pageSize?: number;
  /** Called with the next 1-based page when a control is activated. */
  onPageChange: (page: number) => void;
  /** Page buttons rendered on each side of the current page. Defaults to 1. */
  siblingCount?: number;
  /** Accessible label for the navigation landmark. */
  "aria-label"?: string;
}

export type PaginationItem = number | "ellipsis";
