import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { InputProps } from "./types";

/**
 * Input — the canonical single-line text field.
 *
 * Bundles the full field anatomy (label, description, error/success, inline
 * adornments and icons) with correct wiring: `aria-invalid`,
 * `aria-describedby`, and a programmatic label association. All colours come
 * from semantic tokens, so the field themes automatically (WCAG 2.1 AA).
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    id,
    label,
    description,
    error,
    success,
    prefix,
    suffix,
    leadingIcon,
    trailingIcon,
    action,
    className,
    containerClassName,
    disabled,
    readOnly,
    required,
    "aria-describedby": ariaDescribedBy,
    ...props
  },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = `${inputId}-description`;
  const messageId = `${inputId}-message`;
  const hasError = error != null && error !== false;
  const hasSuccess = !hasError && success != null && success !== false;

  const describedBy =
    [
      ariaDescribedBy,
      description != null ? descriptionId : null,
      hasError || hasSuccess ? messageId : null,
    ]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label != null && (
        <label htmlFor={inputId} className="text-sm font-medium text-foreground">
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <div
        data-slot="input-field"
        data-invalid={hasError || undefined}
        className={cn(
          "flex h-9 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-elevation-1 transition-colors",
          "focus-within:ring-[3px] focus-within:ring-ring/50 focus-within:border-ring",
          hasError && "border-danger focus-within:border-danger focus-within:ring-danger/40",
          hasSuccess && "border-success focus-within:border-success focus-within:ring-success/40",
          disabled && "cursor-not-allowed opacity-50",
          readOnly && "bg-muted",
        )}
      >
        {leadingIcon != null && (
          <span
            className="flex shrink-0 items-center text-muted-foreground [&_svg]:size-4"
            aria-hidden="true"
          >
            {leadingIcon}
          </span>
        )}
        {prefix != null && (
          <span className="shrink-0 text-muted-foreground select-none">{prefix}</span>
        )}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          aria-invalid={hasError || undefined}
          aria-describedby={describedBy}
          className={cn(
            "w-full bg-transparent text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed",
            className,
          )}
          {...props}
        />
        {suffix != null && (
          <span className="shrink-0 text-muted-foreground select-none">{suffix}</span>
        )}
        {trailingIcon != null && (
          <span
            className="flex shrink-0 items-center text-muted-foreground [&_svg]:size-4"
            aria-hidden="true"
          >
            {trailingIcon}
          </span>
        )}
        {action != null && <span className="flex shrink-0 items-center">{action}</span>}
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
      {hasSuccess && (
        <p id={messageId} className="text-xs text-success">
          {success}
        </p>
      )}
    </div>
  );
});
