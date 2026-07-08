import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { SpinnerProps, SpinnerSize } from "./types";

const sizeClasses: Record<SpinnerSize, string> = {
  xs: "size-3 border-2",
  sm: "size-4 border-2",
  md: "size-5 border-2",
  lg: "size-6 border-[3px]",
  xl: "size-8 border-4",
};

/**
 * Spinner — an indeterminate loading indicator. Inherits `currentColor`, so it
 * tints to the surrounding text. Exposes `role="status"` with a visually
 * hidden label for assistive tech, and honours reduced-motion via the global
 * stylesheet (which neutralises `animate-*`).
 */
export const Spinner = forwardRef<HTMLSpanElement, SpinnerProps>(function Spinner(
  { className, size = "md", label = "Загрузка", ...props },
  ref,
) {
  return (
    <span
      ref={ref}
      role="status"
      aria-label={label}
      data-slot="spinner"
      className={cn("inline-flex text-muted-foreground", className)}
      {...props}
    >
      <span
        className={cn(
          "animate-spin rounded-full border-current border-t-transparent",
          sizeClasses[size],
        )}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </span>
  );
});
