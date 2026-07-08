import type { Dialog as DialogPrimitive } from "radix-ui";
import type * as React from "react";

export type DialogContentProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
  /** Hide the built-in close button in the top-right corner. */
  hideCloseButton?: boolean;
  /** Accessible label for the built-in close button. */
  closeLabel?: string;
};

export type DialogOverlayProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>;

export type DialogTitleProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>;

export type DialogDescriptionProps = React.ComponentPropsWithoutRef<
  typeof DialogPrimitive.Description
>;

export type DialogSectionProps = React.HTMLAttributes<HTMLDivElement>;
