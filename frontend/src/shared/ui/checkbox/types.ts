import type { Checkbox as CheckboxPrimitive } from "radix-ui";
import type * as React from "react";

export type CheckboxSize = "sm" | "md";

export interface CheckboxProps
  extends Omit<React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>, "children"> {
  /** Visible label, associated with the control via `htmlFor`/`id`. */
  label?: React.ReactNode;
  /** Helper text shown beneath the control when there is no error. */
  description?: React.ReactNode;
  /** Error message. When set, the control is marked invalid and styled as error. */
  error?: React.ReactNode;
  /** Control box size. */
  size?: CheckboxSize;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
}
