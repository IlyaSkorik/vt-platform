import { Tooltip as TooltipPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { TooltipContentProps, TooltipProviderProps } from "./types";

/**
 * Tooltip — a contextual label built on Radix Tooltip.
 *
 * Radix supplies keyboard (focus) and pointer triggers, collision handling and
 * ARIA wiring; this layer adds the VT popover surface, token-driven z-index and
 * an optional arrow. Wrap the app (or a subtree) in `TooltipProvider` once to
 * share open/close timing (WCAG 2.1 AA).
 */
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipProvider({ delayDuration = 200, ...props }: TooltipProviderProps) {
  return <TooltipPrimitive.Provider delayDuration={delayDuration} {...props} />;
}

export const TooltipContent = forwardRef<HTMLDivElement, TooltipContentProps>(
  function TooltipContent(
    { className, children, withArrow = true, sideOffset = 6, ...props },
    ref,
  ) {
    return (
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          ref={ref}
          data-slot="tooltip-content"
          sideOffset={sideOffset}
          className={cn(
            // Radix reports a tooltip's open state as `delayed-open` or `instant-open`
            // rather than `open`, so both need naming; a bare `data-[state=open]` here
            // would silently never match.
            "z-[var(--z-tooltip)] max-w-xs rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-elevation-2 data-[state=closed]:animate-fade-out data-[state=delayed-open]:animate-fade-in data-[state=instant-open]:animate-fade-in",
            className,
          )}
          {...props}
        >
          {children}
          {withArrow && (
            <TooltipPrimitive.Arrow className="fill-[var(--popover)]" width={10} height={5} />
          )}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    );
  },
);
