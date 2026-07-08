import { RadioGroup as RadioGroupPrimitive } from "radix-ui";
import { createContext, forwardRef, useContext, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { RadioGroupProps, RadioProps, RadioSize } from "./types";

const RadioSizeContext = createContext<RadioSize>("md");

const boxSize = {
  sm: "size-4 [&_svg]:size-2",
  md: "size-5 [&_svg]:size-2.5",
} as const;

/**
 * RadioGroup — a set of mutually exclusive options.
 *
 * Wraps Radix RadioGroup with the shared field anatomy (label, description,
 * error) and roving-focus keyboard navigation. The chosen size cascades to
 * child {@link Radio} items via context. Colours flow through semantic tokens
 * (WCAG 2.1 AA).
 */
export const RadioGroup = forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive.Root>,
  RadioGroupProps
>(function RadioGroup(
  {
    label,
    description,
    error,
    size = "md",
    className,
    containerClassName,
    "aria-describedby": ariaDescribedBy,
    ...props
  },
  ref,
) {
  const generatedId = useId();
  const labelId = `${generatedId}-label`;
  const descriptionId = `${generatedId}-description`;
  const messageId = `${generatedId}-message`;
  const hasError = error != null && error !== false;

  const describedBy =
    [ariaDescribedBy, description != null ? descriptionId : null, hasError ? messageId : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-2", containerClassName)}>
      {label != null && (
        <span id={labelId} className="text-sm font-medium text-foreground">
          {label}
        </span>
      )}
      <RadioSizeContext.Provider value={size}>
        <RadioGroupPrimitive.Root
          ref={ref}
          data-slot="radio-group"
          aria-invalid={hasError || undefined}
          aria-labelledby={label != null ? labelId : undefined}
          aria-describedby={describedBy}
          className={cn(
            "flex gap-3 data-[orientation=vertical]:flex-col data-[orientation=horizontal]:flex-row data-[orientation=horizontal]:flex-wrap",
            className,
          )}
          {...props}
        />
      </RadioSizeContext.Provider>

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
});

/**
 * Radio — a single option within a {@link RadioGroup}.
 *
 * Renders a labelled Radix radio item; the indicator dot uses the primary
 * token when selected.
 */
export const Radio = forwardRef<React.ElementRef<typeof RadioGroupPrimitive.Item>, RadioProps>(
  function Radio({ id, label, description, size, className, disabled, ...props }, ref) {
    const groupSize = useContext(RadioSizeContext);
    const resolvedSize = size ?? groupSize;
    const generatedId = useId();
    const radioId = id ?? generatedId;
    const descriptionId = `${radioId}-description`;

    return (
      <div className="flex items-start gap-2">
        <RadioGroupPrimitive.Item
          ref={ref}
          id={radioId}
          data-slot="radio"
          disabled={disabled}
          aria-describedby={description != null ? descriptionId : undefined}
          className={cn(
            "peer shrink-0 rounded-full border border-input bg-background shadow-elevation-1 outline-none transition-colors",
            "focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring",
            "data-[state=checked]:border-primary data-[state=checked]:text-primary",
            "disabled:cursor-not-allowed disabled:opacity-50",
            boxSize[resolvedSize],
            className,
          )}
          {...props}
        >
          <RadioGroupPrimitive.Indicator className="flex size-full items-center justify-center">
            <span className="block size-full scale-50 rounded-full bg-primary" aria-hidden="true" />
          </RadioGroupPrimitive.Indicator>
        </RadioGroupPrimitive.Item>

        {label != null && (
          <div className="flex flex-col gap-0.5">
            <label
              htmlFor={radioId}
              className="text-sm font-medium text-foreground select-none leading-5 peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
            >
              {label}
            </label>
            {description != null && (
              <p id={descriptionId} className="text-xs text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        )}
      </div>
    );
  },
);
