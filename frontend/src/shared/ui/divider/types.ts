import type { Separator as SeparatorPrimitive } from "radix-ui";
import type * as React from "react";

export type DividerOrientation = "horizontal" | "vertical";

export interface DividerProps
  extends Omit<
    React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>,
    "orientation" | "children"
  > {
  /** Line direction. Defaults to horizontal. */
  orientation?: DividerOrientation;
  /**
   * Purely visual separator with no semantic meaning (removed from the a11y
   * tree). Ignored when a `label` is present, since a labelled divider conveys
   * meaning. Defaults to true.
   */
  decorative?: boolean;
  /** Optional centred label with lines on both sides (horizontal only). */
  label?: React.ReactNode;
}
