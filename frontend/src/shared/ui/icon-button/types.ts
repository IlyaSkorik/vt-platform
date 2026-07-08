import type * as React from "react";
import type { ButtonProps } from "@/shared/ui/button";

export interface IconButtonProps extends Omit<ButtonProps, "iconOnly" | "leftIcon" | "rightIcon"> {
  /** The icon to render. */
  icon: React.ReactNode;
  /** Accessible name — required because the control has no visible text label. */
  "aria-label": string;
}
