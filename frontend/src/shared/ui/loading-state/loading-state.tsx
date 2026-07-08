import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { LoadingStateProps, LoadingStateSize } from "./types";

const spinnerSize: Record<LoadingStateSize, string> = {
  sm: "size-4 border-2",
  md: "size-6 border-2",
  lg: "size-8 border-[3px]",
};

/**
 * LoadingState — a centered spinner with an optional label for full-area
 * loading placeholders. Self-contained (no Spinner dependency): the indicator
 * is a token-styled `animate-spin` ring. Exposes `role="status"` with an
 * accessible name so screen readers announce the pending work (WCAG 2.1 AA).
 */
export const LoadingState = forwardRef<HTMLDivElement, LoadingStateProps>(function LoadingState(
  { label, size = "md", srLabel = "Загрузка", className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      role="status"
      aria-live="polite"
      aria-label={label == null ? srLabel : undefined}
      data-slot="loading-state"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 py-10 text-muted-foreground",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn("animate-spin rounded-full border-muted border-t-primary", spinnerSize[size])}
      />
      {label != null ? (
        <span className="text-sm text-muted-foreground">{label}</span>
      ) : (
        <span className="sr-only">{srLabel}</span>
      )}
    </div>
  );
});
