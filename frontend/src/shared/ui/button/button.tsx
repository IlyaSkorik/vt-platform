import { LoaderCircle } from "lucide-react";
import { Slot } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import { buttonVariants } from "./styles";
import type { ButtonProps } from "./types";

/**
 * Button — the canonical interactive control of the VT design system.
 *
 * Accessible by construction: focus-visible ring, disabled/`aria-disabled`
 * semantics, a busy spinner that keeps layout stable, and `asChild`
 * composition for polymorphic rendering (e.g. router links) without losing
 * keyboard/ARIA behaviour. Colours flow through semantic tokens, so it works
 * in every theme untouched (WCAG 2.1 AA, ARCH-001 §8.3).
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant,
    size,
    iconOnly = false,
    asChild = false,
    loading = false,
    leftIcon,
    rightIcon,
    disabled,
    type,
    children,
    ...props
  },
  ref,
) {
  const Comp = asChild ? Slot.Root : "button";
  const isDisabled = disabled || loading;

  const content = asChild ? (
    children
  ) : (
    <>
      {loading ? (
        <LoaderCircle className="animate-spin" aria-hidden="true" />
      ) : (
        leftIcon != null && <span aria-hidden="true">{leftIcon}</span>
      )}
      {children}
      {!loading && rightIcon != null && <span aria-hidden="true">{rightIcon}</span>}
    </>
  );

  return (
    <Comp
      ref={ref}
      data-slot="button"
      className={cn(buttonVariants({ variant, size, iconOnly }), className)}
      // Explicit type avoids accidental form submission when nested in a form.
      type={asChild ? undefined : (type ?? "button")}
      disabled={asChild ? undefined : isDisabled}
      aria-busy={loading || undefined}
      aria-disabled={asChild && isDisabled ? true : undefined}
      {...props}
    >
      {content}
    </Comp>
  );
});
