import type { Popover as PopoverPrimitive } from "radix-ui";
import type * as React from "react";

export interface PopoverContentProps
  extends React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content> {}
