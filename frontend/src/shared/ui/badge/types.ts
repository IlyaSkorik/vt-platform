import type { VariantProps } from "class-variance-authority";
import type * as React from "react";
import type { badgeVariants } from "./styles";

type BadgeVariantProps = VariantProps<typeof badgeVariants>;

export interface BadgeProps
  extends Omit<React.HTMLAttributes<HTMLSpanElement>, "color">,
    BadgeVariantProps {
  /** Icon rendered before the label. */
  icon?: React.ReactNode;
  /** Render a small leading status dot tinted with the current text colour. */
  dot?: boolean;
}
