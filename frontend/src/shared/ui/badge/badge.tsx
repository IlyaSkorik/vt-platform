import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import { badgeVariants } from "./styles";
import type { BadgeProps } from "./types";

/**
 * Badge — a compact status/label pill. Colours flow through semantic status
 * tokens, so every variant themes automatically (WCAG 2.1 AA). An optional
 * leading icon or status dot decorates the label without affecting semantics.
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { className, variant, size, icon, dot = false, children, ...props },
  ref,
) {
  return (
    <span
      ref={ref}
      data-slot="badge"
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    >
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {icon != null && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
});
