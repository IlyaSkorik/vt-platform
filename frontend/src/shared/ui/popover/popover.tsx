import { Popover as PopoverPrimitive } from "radix-ui";
import { forwardRef } from "react";

import { cn } from "@/shared/lib/cn";
import type { PopoverContentProps } from "./types";

/**
 * Popover — a floating surface anchored to a trigger.
 *
 * Radix owns the hard parts (positioning, focus return, dismiss on outside click
 * or Escape); this adds the surface's own look, which is deliberately the same
 * one `SelectContent` uses so a calendar and a listbox do not read as two
 * different kinds of overlay.
 *
 * Root, Trigger, Anchor and Close pass through unchanged — a popover's content is
 * whatever the caller puts in it, and wrapping them would only add indirection.
 */
export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverAnchor = PopoverPrimitive.Anchor;
export const PopoverClose = PopoverPrimitive.Close;

export const PopoverContent = forwardRef<
  React.ElementRef<typeof PopoverPrimitive.Content>,
  PopoverContentProps
>(function PopoverContent({ className, align = "start", sideOffset = 4, ...props }, ref) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        ref={ref}
        data-slot="popover-content"
        align={align}
        sideOffset={sideOffset}
        className={cn(
          // Fades only, no transform: the popper positions itself with a
          // `translate`, and an animation touching the same property fights it.
          "z-[var(--z-popover)] w-auto rounded-md border border-border bg-popover p-3 text-popover-foreground shadow-elevation-2 outline-none",
          "data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
});
