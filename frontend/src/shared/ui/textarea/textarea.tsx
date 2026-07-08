import { forwardRef, useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { TextareaProps } from "./types";

/**
 * Textarea — the canonical multi-line text field.
 *
 * Mirrors {@link Input}'s field anatomy (label, description, error/success)
 * with the same accessibility wiring (`aria-invalid`, `aria-describedby`).
 * Colours resolve through semantic tokens, so it themes automatically.
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  {
    id,
    label,
    description,
    error,
    success,
    className,
    containerClassName,
    disabled,
    readOnly,
    required,
    rows = 4,
    "aria-describedby": ariaDescribedBy,
    ...props
  },
  ref,
) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const descriptionId = `${fieldId}-description`;
  const messageId = `${fieldId}-message`;
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
        <label htmlFor={fieldId} className="text-sm font-medium text-foreground">
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <textarea
        ref={ref}
        id={fieldId}
        rows={rows}
        disabled={disabled}
        readOnly={readOnly}
        required={required}
        aria-invalid={hasError || undefined}
        aria-describedby={describedBy}
        className={cn(
          "w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-elevation-1 outline-none transition-colors",
          "placeholder:text-muted-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring",
          "disabled:cursor-not-allowed disabled:opacity-50",
          hasError && "border-danger focus-visible:border-danger focus-visible:ring-danger/40",
          hasSuccess && "border-success focus-visible:border-success focus-visible:ring-success/40",
          readOnly && "bg-muted",
          className,
        )}
        {...props}
      />

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
