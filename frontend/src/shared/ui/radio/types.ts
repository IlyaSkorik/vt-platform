import type { RadioGroup as RadioGroupPrimitive } from "radix-ui";
import type * as React from "react";

export type RadioSize = "sm" | "md";

export interface RadioGroupProps
  extends React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root> {
  /** Visible group label, rendered as the fieldset legend. */
  label?: React.ReactNode;
  /** Helper text shown beneath the group when there is no error. */
  description?: React.ReactNode;
  /** Error message. When set, the group is marked invalid and styled as error. */
  error?: React.ReactNode;
  /** Size applied to descendant radio items via context. */
  size?: RadioSize;
  /** Wrapper element class, for layout composition. */
  containerClassName?: string;
}

export interface RadioProps
  extends Omit<React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>, "children"> {
  /** Visible label, associated with the control via `htmlFor`/`id`. */
  label?: React.ReactNode;
  /** Helper text shown beneath the item. */
  description?: React.ReactNode;
  /** Control box size. Falls back to the group size when omitted. */
  size?: RadioSize;
}
