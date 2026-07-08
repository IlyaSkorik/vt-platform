import { Construction } from "lucide-react";
import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { EmptyPageProps } from "./types";

/**
 * EmptyPage — a full-page placeholder for a section that has no content yet
 * (e.g. a shell route whose feature has not shipped).
 *
 * Distinct from `EmptyState` (an inline "no data" block): EmptyPage fills the
 * page body and is a labelled `region` so assistive tech can locate it. All
 * colours resolve through semantic tokens (WCAG 2.1 AA).
 */
export const EmptyPage = forwardRef<HTMLElement, EmptyPageProps>(function EmptyPage(
  { className, icon, title, description, action, ...props },
  ref,
) {
  const titleId = useId();
  return (
    <section
      ref={ref}
      aria-labelledby={titleId}
      data-slot="empty-page"
      className={cn(
        "flex min-h-[60svh] w-full flex-col items-center justify-center gap-4 rounded-xl border border-border border-dashed bg-card/40 px-6 py-16 text-center",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-7"
      >
        {icon ?? <Construction />}
      </span>
      <div className="flex flex-col gap-1.5">
        <p id={titleId} className="font-semibold text-foreground text-lg">
          {title}
        </p>
        {description != null && (
          <p className="max-w-md text-muted-foreground text-sm">{description}</p>
        )}
      </div>
      {action != null && <div className="mt-2 flex items-center gap-2">{action}</div>}
    </section>
  );
});
