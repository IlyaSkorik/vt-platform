import { Switch as SwitchPrimitive } from "radix-ui";
import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { SwitchProps } from "./types";

const track = {
  sm: "h-4 w-7",
  md: "h-5 w-9",
} as const;

const thumb = {
  sm: "size-3 data-[state=checked]:translate-x-3",
  md: "size-4 data-[state=checked]:translate-x-4",
} as const;

/**
 * Switch — an instant on/off toggle for a single setting.
 *
 * Wraps Radix Switch with the shared field anatomy (label, description) and a
 * programmatic label association. The track uses the primary token when on and
 * the input token when off; the thumb slides between states. Colours flow
 * through semantic tokens (WCAG 2.1 AA).
 */
export const Switch = forwardRef<React.ElementRef<typeof SwitchPrimitive.Root>, SwitchProps>(
  function Switch(
    {
      id,
      label,
      description,
      size = "md",
      className,
      containerClassName,
      disabled,
      "aria-describedby": ariaDescribedBy,
      ...props
    },
    ref,
  ) {
    const generatedId = useId();
    const switchId = id ?? generatedId;
    const descriptionId = `${switchId}-description`;

    const describedBy =
      [ariaDescribedBy, description != null ? descriptionId : null].filter(Boolean).join(" ") ||
      undefined;

    return (
      <div className={cn("flex flex-col gap-1.5", containerClassName)}>
        <div className="flex items-center gap-2">
          <SwitchPrimitive.Root
            ref={ref}
            id={switchId}
            data-slot="switch"
            disabled={disabled}
            aria-describedby={describedBy}
            className={cn(
              "peer inline-flex shrink-0 cursor-pointer items-center rounded-full border border-transparent p-0.5 shadow-elevation-1 outline-none transition-colors",
              "focus-visible:ring-[3px] focus-visible:ring-ring/50",
              "data-[state=checked]:bg-primary data-[state=unchecked]:bg-input",
              "disabled:cursor-not-allowed disabled:opacity-50",
              track[size],
              className,
            )}
            {...props}
          >
            <SwitchPrimitive.Thumb
              className={cn(
                "pointer-events-none block rounded-full bg-background shadow-elevation-1 ring-0 transition-transform data-[state=unchecked]:translate-x-0",
                thumb[size],
              )}
            />
          </SwitchPrimitive.Root>

          {label != null && (
            <label
              htmlFor={switchId}
              className="cursor-pointer text-sm font-medium text-foreground select-none peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
            >
              {label}
            </label>
          )}
        </div>

        {description != null && (
          <p id={descriptionId} className="text-xs text-muted-foreground">
            {description}
          </p>
        )}
      </div>
    );
  },
);
