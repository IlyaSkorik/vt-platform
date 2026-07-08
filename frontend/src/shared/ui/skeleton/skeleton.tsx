import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { SkeletonProps, SkeletonVariant } from "./types";

const variantClasses: Record<SkeletonVariant, string> = {
  text: "h-4 w-full rounded-md",
  circle: "rounded-full",
  rect: "rounded-md",
};

/**
 * Skeleton — a decorative loading placeholder. Pulses via `animate-pulse`
 * (honouring reduced-motion through the global stylesheet) and uses the
 * semantic muted token. Hidden from assistive tech by default; size it with
 * `className`.
 */
export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(function Skeleton(
  { className, variant = "rect", "aria-hidden": ariaHidden = true, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      data-slot="skeleton"
      aria-hidden={ariaHidden}
      className={cn("animate-pulse bg-muted", variantClasses[variant], className)}
      {...props}
    />
  );
});
