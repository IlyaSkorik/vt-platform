import type { VariantProps } from "class-variance-authority";
import type * as React from "react";
import type { alertVariants } from "./styles";

type AlertVariantProps = VariantProps<typeof alertVariants>;

export interface AlertProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title" | "color">,
    AlertVariantProps {
  /** Short, prominent heading for the alert. */
  title?: React.ReactNode;
  /**
   * Custom leading icon. Defaults to a per-variant status icon. Pass `null` to
   * render no icon at all.
   */
  icon?: React.ReactNode;
  /** When true, renders a labelled close button that calls `onDismiss`. */
  dismissible?: boolean;
  /** Invoked when the dismiss button is pressed. */
  onDismiss?: () => void;
  /** Accessible label for the dismiss button. */
  dismissLabel?: string;
}
