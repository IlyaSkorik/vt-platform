import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from "lucide-react";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import { alertVariants } from "./styles";
import type { AlertProps } from "./types";

const DEFAULT_ICONS = {
  info: Info,
  success: CircleCheck,
  warning: TriangleAlert,
  danger: CircleAlert,
} as const;

/**
 * Alert — an inline status banner for contextual feedback.
 *
 * Carries a per-variant status icon, optional title/description and an optional
 * dismiss control. Uses `role="alert"` for the critical `danger`/`warning`
 * variants and the politer `role="status"` otherwise. All colours flow through
 * semantic status tokens, so it themes automatically (WCAG 2.1 AA).
 */
export const Alert = forwardRef<HTMLDivElement, AlertProps>(function Alert(
  {
    className,
    variant = "info",
    title,
    icon,
    dismissible = false,
    onDismiss,
    dismissLabel = "Закрыть",
    children,
    ...props
  },
  ref,
) {
  const resolvedVariant = variant ?? "info";
  const Icon = DEFAULT_ICONS[resolvedVariant];
  const isCritical = resolvedVariant === "danger" || resolvedVariant === "warning";

  return (
    <div
      ref={ref}
      data-slot="alert"
      role={isCritical ? "alert" : "status"}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      {icon !== null && (
        <span className="mt-0.5 flex shrink-0 [&_svg]:size-5" aria-hidden="true">
          {icon ?? <Icon />}
        </span>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {title != null && <p className="font-medium leading-none">{title}</p>}
        {children != null && <div className="text-sm opacity-90">{children}</div>}
      </div>
      {dismissible && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label={dismissLabel}
          className="-mr-1 -mt-1 flex shrink-0 rounded-sm p-1 opacity-70 outline-none transition-opacity hover:opacity-100 focus-visible:ring-[3px] focus-visible:ring-ring/50 [&_svg]:size-4"
        >
          <X aria-hidden="true" />
        </button>
      )}
    </div>
  );
});
