import type { Dialog as DialogPrimitive } from "radix-ui";
import type * as React from "react";

export type DrawerSide = "left" | "right" | "top" | "bottom";

export type DrawerContentProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
  /** Edge the drawer slides in from. Defaults to `"right"`. */
  side?: DrawerSide;
  /** Hide the built-in close button in the top-right corner. */
  hideCloseButton?: boolean;
  /** Accessible label for the built-in close button. */
  closeLabel?: string;
};

export type DrawerOverlayProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>;

export type DrawerTitleProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>;

export type DrawerDescriptionProps = React.ComponentPropsWithoutRef<
  typeof DialogPrimitive.Description
>;

export type DrawerSectionProps = React.HTMLAttributes<HTMLDivElement>;
