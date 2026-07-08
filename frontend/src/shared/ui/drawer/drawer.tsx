import { X } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type {
  DrawerContentProps,
  DrawerDescriptionProps,
  DrawerOverlayProps,
  DrawerSectionProps,
  DrawerSide,
  DrawerTitleProps,
} from "./types";

const SIDE_STYLES: Record<DrawerSide, string> = {
  left: "inset-y-0 left-0 h-full w-3/4 max-w-sm border-r",
  right: "inset-y-0 right-0 h-full w-3/4 max-w-sm border-l",
  top: "inset-x-0 top-0 w-full max-h-[80vh] border-b",
  bottom: "inset-x-0 bottom-0 w-full max-h-[80vh] border-t",
};

/**
 * Drawer — a side sheet built on Radix Dialog.
 *
 * Reuses the Dialog focus trap, `Escape`-to-close and ARIA wiring, but pins the
 * content to a screen edge via the `side` prop. Content MUST include a
 * `DrawerTitle` for an accessible name (WCAG 2.1 AA).
 */
export const Drawer = DialogPrimitive.Root;
export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;
export const DrawerPortal = DialogPrimitive.Portal;

export const DrawerOverlay = forwardRef<HTMLDivElement, DrawerOverlayProps>(function DrawerOverlay(
  { className, ...props },
  ref,
) {
  return (
    <DialogPrimitive.Overlay
      ref={ref}
      data-slot="drawer-overlay"
      className={cn(
        "fixed inset-0 z-[var(--z-overlay)] bg-foreground/40 backdrop-blur-sm transition-opacity data-[state=closed]:opacity-0 data-[state=open]:opacity-100",
        className,
      )}
      {...props}
    />
  );
});

export const DrawerContent = forwardRef<HTMLDivElement, DrawerContentProps>(function DrawerContent(
  {
    className,
    children,
    side = "right",
    hideCloseButton = false,
    closeLabel = "Закрыть",
    ...props
  },
  ref,
) {
  return (
    <DrawerPortal>
      <DrawerOverlay />
      <DialogPrimitive.Content
        ref={ref}
        data-slot="drawer-content"
        data-side={side}
        className={cn(
          "fixed z-[var(--z-modal)] flex flex-col gap-4 bg-popover p-6 text-popover-foreground shadow-elevation-3 transition-transform",
          SIDE_STYLES[side],
          className,
        )}
        {...props}
      >
        {children}
        {!hideCloseButton && (
          <DialogPrimitive.Close
            aria-label={closeLabel}
            className="absolute right-4 top-4 flex rounded-sm p-1 opacity-70 outline-none transition-opacity hover:opacity-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 [&_svg]:size-4"
          >
            <X aria-hidden="true" />
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DrawerPortal>
  );
});

export function DrawerHeader({ className, ...props }: DrawerSectionProps) {
  return (
    <div
      data-slot="drawer-header"
      className={cn("flex flex-col gap-1.5 pr-6 text-left", className)}
      {...props}
    />
  );
}

export function DrawerFooter({ className, ...props }: DrawerSectionProps) {
  return (
    <div
      data-slot="drawer-footer"
      className={cn("mt-auto flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)}
      {...props}
    />
  );
}

export const DrawerTitle = forwardRef<HTMLHeadingElement, DrawerTitleProps>(function DrawerTitle(
  { className, ...props },
  ref,
) {
  return (
    <DialogPrimitive.Title
      ref={ref}
      data-slot="drawer-title"
      className={cn("text-lg font-semibold leading-none text-foreground", className)}
      {...props}
    />
  );
});

export const DrawerDescription = forwardRef<HTMLParagraphElement, DrawerDescriptionProps>(
  function DrawerDescription({ className, ...props }, ref) {
    return (
      <DialogPrimitive.Description
        ref={ref}
        data-slot="drawer-description"
        className={cn("text-sm text-muted-foreground", className)}
        {...props}
      />
    );
  },
);
