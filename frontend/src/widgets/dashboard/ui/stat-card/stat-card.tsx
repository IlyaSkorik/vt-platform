import type { LucideIcon } from "lucide-react";
import { RotateCw, TriangleAlert } from "lucide-react";
import { cn } from "@/shared/lib";
import { Card, CardContent, IconButton, Skeleton } from "@/shared/ui";
import type { StatTone, TrendDirection, WidgetStatus } from "../../model";
import { TREND_GLYPH } from "../../model";

/** Tone → icon-chip surface classes (semantic status tokens only). */
const TONE_CHIP: Record<StatTone, string> = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success-surface text-success",
  warning: "bg-warning-surface text-warning",
  info: "bg-info-surface text-info",
  neutral: "bg-muted text-muted-foreground",
};

/** Trend direction → delta-text colour. `flat` stays muted (no signal). */
const TREND_COLOR: Record<TrendDirection, string> = {
  up: "text-success",
  down: "text-danger",
  flat: "text-muted-foreground",
};

export interface StatCardProps {
  /** Metric label (e.g. "Участники"). */
  label: string;
  icon: LucideIcon;
  tone: StatTone;
  status: WidgetStatus;
  /** Pre-formatted primary value (localized). Required in the success state. */
  value?: string;
  /** Pre-formatted signed delta (e.g. "+12,5 %"). */
  delta?: string;
  trend?: TrendDirection;
  /** Copy shown in the empty state (e.g. "Нет данных"). */
  emptyLabel?: string;
  /** Retry handler surfaced in the error state. */
  onRetry?: () => void;
}

/**
 * StatCard — a single headline-metric tile with an explicit four-state
 * contract (loading / empty / error / success).
 *
 * The reusable statistics widget the dashboard grid is built from: an
 * icon chip toned by semantic status tokens, the metric value and a
 * period-over-period delta. Success renders the number + trend; loading shows
 * a skeleton; empty and error render inline, self-contained messages so the
 * grid never collapses. Token-only, themes automatically.
 */
export function StatCard({
  label,
  icon: Icon,
  tone,
  status,
  value,
  delta,
  trend = "flat",
  emptyLabel = "Нет данных",
  onRetry,
}: StatCardProps): React.JSX.Element {
  return (
    <Card aria-label={label} aria-busy={status === "loading"} className="h-full">
      <CardContent className="flex items-start gap-4 p-5">
        <span
          aria-hidden="true"
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-lg [&_svg]:size-5",
            status === "error" ? "bg-danger-surface text-danger" : TONE_CHIP[tone],
          )}
        >
          {status === "error" ? <TriangleAlert /> : <Icon />}
        </span>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="truncate font-medium text-muted-foreground text-sm">{label}</p>

          {status === "loading" && <Skeleton className="mt-1 h-7 w-24" />}

          {status === "error" && (
            <div className="flex items-center gap-2">
              <span className="text-danger text-sm">Ошибка загрузки</span>
              {onRetry && (
                <IconButton
                  size="xs"
                  variant="ghost"
                  aria-label={`Повторить загрузку: ${label}`}
                  icon={<RotateCw />}
                  onClick={onRetry}
                />
              )}
            </div>
          )}

          {status === "empty" && (
            <p className="font-semibold text-foreground text-xl">{emptyLabel}</p>
          )}

          {status === "success" && (
            <>
              <p className="font-bold text-2xl text-foreground tracking-tight tabular-nums">
                {value}
              </p>
              {delta != null && (
                <p className={cn("flex items-center gap-1 text-xs", TREND_COLOR[trend])}>
                  <span aria-hidden="true">{TREND_GLYPH[trend]}</span>
                  <span>{delta}</span>
                  <span className="text-muted-foreground">за месяц</span>
                </p>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
