import { ChevronLeft, ChevronRight } from "lucide-react";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import { getPaginationRange } from "./get-pagination-range";
import type { PaginationProps } from "./types";

const itemBase =
  "inline-flex h-9 min-w-9 items-center justify-center rounded-md px-2 text-sm font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4";

/**
 * Pagination — a controlled page navigator. Renders an accessible `nav`
 * landmark with previous/next controls and numbered page buttons, collapsing
 * long ranges with ellipses. The current page carries `aria-current="page"`;
 * bounds disable the edge controls. Pure and controlled (WCAG 2.1 AA).
 */
export const Pagination = forwardRef<HTMLElement, PaginationProps>(function Pagination(
  {
    page,
    pageCount,
    total,
    pageSize,
    onPageChange,
    siblingCount = 1,
    className,
    "aria-label": ariaLabel = "Пагинация",
    ...props
  },
  ref,
) {
  const resolvedCount =
    pageCount ??
    (total != null && pageSize != null && pageSize > 0 ? Math.ceil(total / pageSize) : 0);

  if (resolvedCount <= 0) {
    return null;
  }

  const current = Math.min(Math.max(page, 1), resolvedCount);
  const items = getPaginationRange(current, resolvedCount, siblingCount);
  const isFirst = current <= 1;
  const isLast = current >= resolvedCount;

  return (
    <nav
      ref={ref}
      aria-label={ariaLabel}
      data-slot="pagination"
      className={cn("flex items-center gap-1", className)}
      {...props}
    >
      <button
        type="button"
        aria-label="Предыдущая страница"
        disabled={isFirst}
        onClick={() => onPageChange(current - 1)}
        className={cn(
          itemBase,
          "gap-1 text-foreground hover:bg-accent hover:text-accent-foreground",
        )}
      >
        <ChevronLeft aria-hidden="true" />
      </button>

      <ul className="flex items-center gap-1">
        {items.map((item, index) => {
          if (item === "ellipsis") {
            // Keyed by the preceding page number: the left and right ellipses
            // always follow different pages, so keys stay unique and stable.
            const previous = items[index - 1];
            return (
              <li
                key={`ellipsis-after-${typeof previous === "number" ? previous : "start"}`}
                aria-hidden="true"
              >
                <span className={cn(itemBase, "text-muted-foreground")}>…</span>
              </li>
            );
          }

          const isActive = item === current;
          return (
            <li key={item}>
              <button
                type="button"
                aria-label={`Страница ${item}`}
                aria-current={isActive ? "page" : undefined}
                onClick={() => onPageChange(item)}
                className={cn(
                  itemBase,
                  isActive
                    ? "bg-primary text-primary-foreground shadow-elevation-1 hover:bg-primary/90"
                    : "text-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                {item}
              </button>
            </li>
          );
        })}
      </ul>

      <button
        type="button"
        aria-label="Следующая страница"
        disabled={isLast}
        onClick={() => onPageChange(current + 1)}
        className={cn(
          itemBase,
          "gap-1 text-foreground hover:bg-accent hover:text-accent-foreground",
        )}
      >
        <ChevronRight aria-hidden="true" />
      </button>
    </nav>
  );
});
