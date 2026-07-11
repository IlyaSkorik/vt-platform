import { Check, CloudOff, Loader2 } from "lucide-react";
import { AUTOSAVE_LABELS, type AutosaveState } from "@/features/competitions";
import { cn } from "@/shared/lib";

interface AutosaveIndicatorProps {
  state: AutosaveState;
  className?: string;
}

export function AutosaveIndicator({ state, className }: AutosaveIndicatorProps): React.JSX.Element {
  const Icon =
    state === "saving" ? Loader2 : state === "saved" ? Check : state === "error" ? CloudOff : null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-muted-foreground text-xs",
        state === "dirty" && "text-warning",
        state === "error" && "text-danger",
        state === "saved" && "text-success",
        className,
      )}
      aria-live="polite"
    >
      {Icon ? (
        <Icon className={cn("size-3.5", state === "saving" && "animate-spin")} aria-hidden="true" />
      ) : null}
      {AUTOSAVE_LABELS[state]}
    </span>
  );
}
