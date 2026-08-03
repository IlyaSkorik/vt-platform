import { X } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type {
  DialogContentProps,
  DialogDescriptionProps,
  DialogOverlayProps,
  DialogSectionProps,
  DialogTitleProps,
} from "./types";

/**
 * Dialog — a modal overlay built on Radix Dialog.
 *
 * Radix supplies the focus trap, `Escape`-to-close, scroll locking and full
 * ARIA wiring; this layer adds the VT surface, token-driven overlay and a
 * consistent close affordance. Content MUST include a `DialogTitle` for an
 * accessible name (WCAG 2.1 AA).
 */
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogPortal = DialogPrimitive.Portal;

export const DialogOverlay = forwardRef<HTMLDivElement, DialogOverlayProps>(function DialogOverlay(
  { className, ...props },
  ref,
) {
  return (
    <DialogPrimitive.Overlay
      ref={ref}
      data-slot="dialog-overlay"
      className={cn(
        // Keyframes, not a transition: Radix inserts this already in its open state, so
        // a transition has nothing to move from — which is why the scrim used to appear
        // in one frame. The animation also holds the node long enough for the closing
        // half to be seen, since Radix waits for `animationend` before unmounting.
        "fixed inset-0 z-[var(--z-overlay)] bg-scrim backdrop-blur-sm data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in",
        className,
      )}
      {...props}
    />
  );
});

export const DialogContent = forwardRef<HTMLDivElement, DialogContentProps>(function DialogContent(
  { className, children, hideCloseButton = false, closeLabel = "Закрыть", ...props },
  ref,
) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        data-slot="dialog-content"
        className={cn(
          // `modal-*` carries the centring offset inside its keyframes — see the note in
          // motion.css — so this must stay centred with the same two translate classes.
          "fixed left-1/2 top-1/2 z-[var(--z-modal)] flex w-full max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-lg border bg-popover p-6 text-popover-foreground shadow-elevation-3 data-[state=closed]:animate-modal-out data-[state=open]:animate-modal-in",
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
    </DialogPortal>
  );
});

export function DialogHeader({ className, ...props }: DialogSectionProps) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-1.5 pr-6 text-left", className)}
      {...props}
    />
  );
}

export function DialogFooter({ className, ...props }: DialogSectionProps) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)}
      {...props}
    />
  );
}

export const DialogTitle = forwardRef<HTMLHeadingElement, DialogTitleProps>(function DialogTitle(
  { className, ...props },
  ref,
) {
  return (
    <DialogPrimitive.Title
      ref={ref}
      data-slot="dialog-title"
      className={cn("text-lg font-semibold leading-none text-foreground", className)}
      {...props}
    />
  );
});

export const DialogDescription = forwardRef<HTMLParagraphElement, DialogDescriptionProps>(
  function DialogDescription({ className, ...props }, ref) {
    return (
      <DialogPrimitive.Description
        ref={ref}
        data-slot="dialog-description"
        className={cn("text-sm text-muted-foreground", className)}
        {...props}
      />
    );
  },
);
