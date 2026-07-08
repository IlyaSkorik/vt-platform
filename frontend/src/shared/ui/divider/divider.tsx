import { Separator as SeparatorPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { DividerProps } from "./types";

/**
 * Divider — a thin rule that separates content (Radix Separator). Supports
 * horizontal/vertical orientation and an optional centred label (horizontal
 * only). Colour flows through the semantic border token, so it themes
 * automatically. A labelled divider is treated as meaningful, not decorative.
 */
export const Divider = forwardRef<HTMLDivElement, DividerProps>(function Divider(
  { className, orientation = "horizontal", decorative = true, label, ...props },
  ref,
) {
  if (label != null && orientation === "horizontal") {
    return (
      <div
        ref={ref}
        data-slot="divider"
        className={cn("flex items-center gap-3", className)}
        {...props}
      >
        <SeparatorPrimitive.Root
          decorative
          orientation="horizontal"
          className="h-px flex-1 bg-border"
        />
        <span className="shrink-0 text-xs font-medium text-muted-foreground">{label}</span>
        <SeparatorPrimitive.Root
          decorative
          orientation="horizontal"
          className="h-px flex-1 bg-border"
        />
      </div>
    );
  }

  return (
    <SeparatorPrimitive.Root
      ref={ref}
      data-slot="divider"
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className,
      )}
      {...props}
    />
  );
});
