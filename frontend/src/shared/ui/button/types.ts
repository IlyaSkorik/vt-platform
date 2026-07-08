import type { VariantProps } from "class-variance-authority";
import type * as React from "react";
import type { buttonVariants } from "./styles";

type ButtonVariantProps = VariantProps<typeof buttonVariants>;

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "color">,
    Omit<ButtonVariantProps, "iconOnly"> {
  /** Render the provided child as the button (Radix `Slot`) for polymorphism. */
  asChild?: boolean;
  /** Show a spinner and disable interaction while an async action is pending. */
  loading?: boolean;
  /** Icon rendered before the label. */
  leftIcon?: React.ReactNode;
  /** Icon rendered after the label. */
  rightIcon?: React.ReactNode;
  /**
   * Square, label-less button. `aria-label` becomes required at the type level
   * so an icon-only control is never shipped without an accessible name.
   */
  iconOnly?: boolean;
}
