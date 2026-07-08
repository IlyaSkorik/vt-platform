import type { Tooltip as TooltipPrimitive } from "radix-ui";
import type * as React from "react";

export type TooltipProps = React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Root>;

export type TooltipProviderProps = React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Provider>;

export type TooltipContentProps = React.ComponentPropsWithoutRef<
  typeof TooltipPrimitive.Content
> & {
  /** Render the small directional arrow. Defaults to `true`. */
  withArrow?: boolean;
};
