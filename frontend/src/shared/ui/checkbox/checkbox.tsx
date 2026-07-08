import { Check, Minus } from "lucide-react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";
import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { CheckboxProps } from "./types";

const boxSize = {
  sm: "size-4 [&_svg]:size-3",
  md: "size-5 [&_svg]:size-3.5",
} as const;

/**
 * Checkbox — a binary (or indeterminate) selection control.
 *
 * Wraps Radix Checkbox with the shared field anatomy (label, description,
 * error) and correct wiring: programmatic label association, `aria-invalid`
 * and `aria-describedby`. Colours flow through semantic tokens, so it themes
 * automatically (WCAG 2.1 AA).
 */
export const Checkbox = forwardRef<React.ElementRef<typeof CheckboxPrimitive.Root>, CheckboxProps>(
  function Checkbox(
    {
      id,
      label,
      description,
      error,
      size = "md",
      className,
      containerClassName,
      disabled,
      required,
      checked,
      "aria-describedby": ariaDescribedBy,
      ...props
    },
    ref,
  ) {
    const generatedId = useId();
    const checkboxId = id ?? generatedId;
    const descriptionId = `${checkboxId}-description`;
    const messageId = `${checkboxId}-message`;
    const hasError = error != null && error !== false;

    const describedBy =
      [ariaDescribedBy, description != null ? descriptionId : null, hasError ? messageId : null]
        .filter(Boolean)
        .join(" ") || undefined;

    return (
      <div className={cn("flex flex-col gap-1.5", containerClassName)}>
        <div className="flex items-start gap-2">
          <CheckboxPrimitive.Root
            ref={ref}
            id={checkboxId}
            data-slot="checkbox"
            aria-invalid={hasError || undefined}
            aria-describedby={describedBy}
            {...(disabled != null ? { disabled } : {})}
            {...(required != null ? { required } : {})}
            {...(checked != null ? { checked } : {})}
            className={cn(
              "peer shrink-0 rounded-sm border border-input bg-background shadow-elevation-1 outline-none transition-colors",
              "focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring",
              "data-[state=checked]:bg-primary data-[state=checked]:border-primary data-[state=checked]:text-primary-foreground",
              "data-[state=indeterminate]:bg-primary data-[state=indeterminate]:border-primary data-[state=indeterminate]:text-primary-foreground",
              "disabled:cursor-not-allowed disabled:opacity-50",
              hasError && "border-danger focus-visible:ring-danger/40 focus-visible:border-danger",
              boxSize[size],
              className,
            )}
            {...props}
          >
            <CheckboxPrimitive.Indicator className="flex items-center justify-center text-current">
              {checked === "indeterminate" ? (
                <Minus aria-hidden="true" />
              ) : (
                <Check aria-hidden="true" />
              )}
            </CheckboxPrimitive.Indicator>
          </CheckboxPrimitive.Root>

          {label != null && (
            <label
              htmlFor={checkboxId}
              className={cn(
                "text-sm font-medium text-foreground select-none peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
                size === "md" && "leading-5",
              )}
            >
              {label}
              {required && (
                <span className="ml-0.5 text-danger" aria-hidden="true">
                  *
                </span>
              )}
            </label>
          )}
        </div>

        {description != null && !hasError && (
          <p id={descriptionId} className="text-xs text-muted-foreground">
            {description}
          </p>
        )}
        {hasError && (
          <p id={messageId} className="text-xs text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
