import { Toaster as SonnerToaster } from "sonner";
import { cn } from "@/shared/lib/cn";
import type { ToasterProps } from "./types";

/**
 * Toaster — the VT-themed mount point for notifications, wrapping Sonner.
 *
 * Render it once near the app root; fire toasts anywhere with the re-exported
 * {@link toast} helper. Sonner owns the queue, stacking, timing and a11y live
 * region; this wrapper only maps its slots onto semantic tokens so toasts match
 * the design system in every theme (WCAG 2.1 AA).
 */
export function Toaster({ className, toastOptions, ...props }: ToasterProps) {
  return (
    <SonnerToaster
      className={cn("toaster", className)}
      toastOptions={{
        ...toastOptions,
        classNames: {
          toast:
            "!bg-popover !text-popover-foreground !border !border-border !shadow-elevation-2 !rounded-md",
          title: "!text-popover-foreground !font-medium",
          description: "!text-muted-foreground",
          actionButton: "!bg-primary !text-primary-foreground !rounded-md",
          cancelButton: "!bg-muted !text-muted-foreground !rounded-md",
          closeButton: "!bg-popover !text-popover-foreground !border-border",
          success: "!text-success",
          error: "!text-danger",
          warning: "!text-warning",
          info: "!text-info",
          ...toastOptions?.classNames,
        },
      }}
      {...props}
    />
  );
}

export { toast } from "sonner";
