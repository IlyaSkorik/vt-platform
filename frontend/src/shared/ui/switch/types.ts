import type { Switch as SwitchPrimitive } from "radix-ui";
import type * as React from "react";

export type SwitchSize = "sm" | "md";

export interface SwitchProps
  extends Omit<React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>, "children"> {
  /** Visible label, associated with the control via `htmlFor`/`id`. */
  label?: React.ReactNode;
  /** Helper text shown beneath the control. */
  description?: React.ReactNode;
  /** Control size. */
  size?: SwitchSize;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
}
