import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type * as React from "react";
import { cn } from "@/shared/lib/cn";

/**
 * Button — the canonical interactive control, owned in-repo (shadcn/ui,
 * Radix-backed). Accessible by construction: focus-visible ring, disabled
 * semantics, and `asChild` composition for polymorphic rendering (e.g. links)
 * without losing keyboard/ARIA behaviour (WCAG 2.1 AA, ARCH-001 §8.3).
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-elevation-1 hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground shadow-elevation-1 hover:bg-destructive/90",
        outline:
          "border border-input bg-background shadow-elevation-1 hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-elevation-1 hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 rounded-md px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render the child element as the button (Radix Slot) instead of a `<button>`. */
  asChild?: boolean;
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  type,
  ...props
}: ButtonProps): React.JSX.Element {
  const Comp = asChild ? Slot.Root : "button";
  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      // Explicit type avoids accidental form submission when used inside forms.
      type={asChild ? undefined : (type ?? "button")}
      {...props}
    />
  );
}

export { buttonVariants };
