import { forwardRef } from "react";
import { Button } from "@/shared/ui/button";
import type { IconButtonProps } from "./types";

/**
 * IconButton — a square, label-less Button for toolbar/compact actions.
 *
 * Delegates all visuals and behaviour to {@link Button} with `iconOnly`, so it
 * inherits variants, sizes, loading and keyboard handling for free. The
 * `aria-label` is required at the type level so an unlabelled icon control can
 * never ship (WCAG 2.1 AA).
 */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon, children, ...props },
  ref,
) {
  return (
    <Button ref={ref} iconOnly {...props}>
      {icon}
      {children}
    </Button>
  );
});
