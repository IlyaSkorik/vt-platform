import { Inbox } from "lucide-react";
import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { EmptyStateProps } from "./types";

/**
 * EmptyState — a centered placeholder for "no data" screens. Composes an
 * icon/illustration slot, a title, optional description and an action slot.
 * Rendered as a labelled `section` (region landmark) so assistive tech can
 * locate the empty message; all colours resolve through semantic tokens
 * (WCAG 2.1 AA).
 */
export const EmptyState = forwardRef<HTMLElement, EmptyStateProps>(function EmptyState(
  { icon, title, description, action, className, ...props },
  ref,
) {
  const titleId = useId();
  return (
    <section
      ref={ref}
      aria-labelledby={titleId}
      data-slot="empty-state"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-6"
      >
        {icon ?? <Inbox />}
      </span>
      <div className="flex flex-col gap-1">
        <p id={titleId} className="text-base font-medium text-foreground">
          {title}
        </p>
        {description != null && (
          <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action != null && <div className="mt-2 flex items-center gap-2">{action}</div>}
    </section>
  );
});
