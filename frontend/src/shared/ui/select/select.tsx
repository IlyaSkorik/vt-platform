import { Check, ChevronDown, ChevronUp } from "lucide-react";
import { Select as SelectPrimitive } from "radix-ui";
import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type {
  SelectContentProps,
  SelectItemProps,
  SelectLabelProps,
  SelectOptionGroup,
  SelectProps,
  SelectSeparatorProps,
  SelectTriggerProps,
} from "./types";

const triggerSize = {
  sm: "h-8 text-sm",
  md: "h-9 text-sm",
} as const;

/** Root, Group and Value are re-exported unchanged for headless composition. */
export const SelectRoot = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;

/** SelectTrigger — the button that opens the listbox; shows the chosen value. */
export const SelectTrigger = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  SelectTriggerProps
>(function SelectTrigger({ size = "md", invalid, className, children, ...props }, ref) {
  return (
    <SelectPrimitive.Trigger
      ref={ref}
      data-slot="select-trigger"
      aria-invalid={invalid || undefined}
      className={cn(
        "flex w-full cursor-pointer items-center justify-between gap-2 rounded-md border border-input bg-background px-3 text-foreground shadow-elevation-1 outline-none transition-colors",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring",
        "data-[placeholder]:text-muted-foreground",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "[&_svg]:size-4 [&_svg]:shrink-0",
        invalid && "border-danger focus-visible:ring-danger/40 focus-visible:border-danger",
        triggerSize[size],
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="text-muted-foreground" aria-hidden="true" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
});

/** SelectContent — the portalled, positioned listbox surface. */
export const SelectContent = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  SelectContentProps
>(function SelectContent({ className, children, position = "popper", ...props }, ref) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        ref={ref}
        data-slot="select-content"
        position={position}
        className={cn(
          // Fades only. The popper below positions itself with a `translate`, so an
          // animation touching `transform` would fight it — and a listbox that slides is
          // harder to read than one that simply arrives.
          "relative z-[var(--z-popover)] max-h-(--radix-select-content-available-height) min-w-[8rem] overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-elevation-2 pointer-events-auto data-[state=closed]:animate-fade-out data-[state=open]:animate-fade-in",
          position === "popper" &&
            "w-full min-w-(--radix-select-trigger-width) data-[side=bottom]:translate-y-1 data-[side=top]:-translate-y-1",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.ScrollUpButton className="flex h-6 items-center justify-center text-muted-foreground">
          <ChevronUp className="size-4" aria-hidden="true" />
        </SelectPrimitive.ScrollUpButton>
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
        <SelectPrimitive.ScrollDownButton className="flex h-6 items-center justify-center text-muted-foreground">
          <ChevronDown className="size-4" aria-hidden="true" />
        </SelectPrimitive.ScrollDownButton>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
});

/** SelectItem — a single option row with a check indicator when selected. */
export const SelectItem = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  SelectItemProps
>(function SelectItem({ className, children, ...props }, ref) {
  return (
    <SelectPrimitive.Item
      ref={ref}
      data-slot="select-item"
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center gap-2 rounded-sm py-1.5 pr-8 pl-2 text-sm text-popover-foreground outline-none",
        "focus:bg-accent focus:text-accent-foreground data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <span className="absolute right-2 flex items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4" aria-hidden="true" />
        </SelectPrimitive.ItemIndicator>
      </span>
    </SelectPrimitive.Item>
  );
});

/** SelectLabel — a non-interactive heading for a group of options. */
export const SelectLabel = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  SelectLabelProps
>(function SelectLabel({ className, ...props }, ref) {
  return (
    <SelectPrimitive.Label
      ref={ref}
      data-slot="select-label"
      className={cn("px-2 py-1.5 text-xs font-medium text-muted-foreground", className)}
      {...props}
    />
  );
});

/** SelectSeparator — a thin divider between option groups. */
export const SelectSeparator = forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  SelectSeparatorProps
>(function SelectSeparator({ className, ...props }, ref) {
  return (
    <SelectPrimitive.Separator
      ref={ref}
      data-slot="select-separator"
      className={cn("-mx-1 my-1 h-px bg-border", className)}
      {...props}
    />
  );
});

function isGrouped(options: SelectProps["options"]): options is SelectOptionGroup[] {
  const first = options[0];
  return first != null && "options" in first;
}

/**
 * Select — a fully-wired dropdown built on Radix Select.
 *
 * Bundles the shared field anatomy (label, description, error, required
 * asterisk) with correct `aria-invalid`/`aria-describedby` wiring and accepts
 * flat or grouped options. For bespoke layouts compose the exported parts
 * (`SelectRoot`, `SelectTrigger`, `SelectContent`, …) directly. Colours flow
 * through semantic tokens (WCAG 2.1 AA).
 */
export const Select = forwardRef<React.ElementRef<typeof SelectPrimitive.Trigger>, SelectProps>(
  function Select(
    {
      options,
      placeholder,
      label,
      description,
      error,
      required,
      size = "md",
      className,
      containerClassName,
      id,
      disabled,
      "aria-describedby": ariaDescribedBy,
      ...props
    },
    ref,
  ) {
    const generatedId = useId();
    const triggerId = id ?? generatedId;
    const descriptionId = `${triggerId}-description`;
    const messageId = `${triggerId}-message`;
    const hasError = error != null && error !== false;

    const describedBy =
      [ariaDescribedBy, description != null ? descriptionId : null, hasError ? messageId : null]
        .filter(Boolean)
        .join(" ") || undefined;

    return (
      <div className={cn("flex flex-col gap-1.5", containerClassName)}>
        {label != null && (
          <label htmlFor={triggerId} className="text-sm font-medium text-foreground">
            {label}
            {required && (
              <span className="ml-0.5 text-danger" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}

        <SelectPrimitive.Root
          {...(disabled != null ? { disabled } : {})}
          {...(required != null ? { required } : {})}
          {...props}
        >
          <SelectTrigger
            ref={ref}
            id={triggerId}
            size={size}
            invalid={hasError}
            className={className}
            aria-describedby={describedBy}
          >
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {isGrouped(options)
              ? options.map((group) => (
                  <SelectGroup key={group.options.map((option) => option.value).join("|")}>
                    <SelectLabel>{group.label}</SelectLabel>
                    {group.options.map((option) => (
                      <SelectItem
                        key={option.value}
                        value={option.value}
                        {...(option.disabled != null ? { disabled: option.disabled } : {})}
                      >
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))
              : options.map((option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    {...(option.disabled != null ? { disabled: option.disabled } : {})}
                  >
                    {option.label}
                  </SelectItem>
                ))}
          </SelectContent>
        </SelectPrimitive.Root>

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
