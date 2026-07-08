import type { LucideIcon } from "lucide-react";
import { Award, ClipboardList, Trophy, Users, Wallet } from "lucide-react";
import { useDashboardStats } from "../../api";
import type { StatKey, StatMetric, StatTone, WidgetStatus } from "../../model";
import { formatMoney, formatNumber, formatPercent, STAT_LABELS } from "../../model";
import { StatCard } from "../stat-card";

/** Static presentation config per metric (icon + accent tone). */
const STAT_CONFIG: Record<StatKey, { icon: LucideIcon; tone: StatTone }> = {
  participants: { icon: Users, tone: "primary" },
  competitions: { icon: Trophy, tone: "info" },
  applications: { icon: ClipboardList, tone: "warning" },
  results: { icon: Award, tone: "success" },
  finance: { icon: Wallet, tone: "neutral" },
};

/** Stable render order of the five headline metrics. */
const STAT_ORDER: readonly StatKey[] = [
  "participants",
  "competitions",
  "applications",
  "results",
  "finance",
];

/** Format a metric's primary value — currency for finance, grouped int otherwise. */
function formatValue(metric: StatMetric): string {
  if (metric.key === "finance") {
    return formatMoney(metric.value, metric.currency ?? "BYN");
  }
  return formatNumber(metric.value);
}

/**
 * StatsGrid — the headline statistics row, wired to {@link useDashboardStats}.
 *
 * Renders the five metric tiles in a fixed order so the layout is stable across
 * loading and success. Each tile derives its own state from the shared query:
 * every card shows a skeleton while loading and an inline retry on error, so a
 * transient failure never blanks the whole row.
 */
export function StatsGrid(): React.JSX.Element {
  const query = useDashboardStats();
  const byKey = new Map((query.data ?? []).map((metric) => [metric.key, metric]));

  const status: WidgetStatus = query.isLoading ? "loading" : query.isError ? "error" : "success";

  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {STAT_ORDER.map((key) => {
        const config = STAT_CONFIG[key];
        const metric = byKey.get(key);
        return (
          <li key={key}>
            <StatCard
              label={STAT_LABELS[key]}
              icon={config.icon}
              tone={config.tone}
              status={status}
              onRetry={() => query.refetch()}
              {...(metric
                ? {
                    value: formatValue(metric),
                    delta: formatPercent(metric.deltaPct),
                    trend: metric.trend,
                  }
                : {})}
            />
          </li>
        );
      })}
    </ul>
  );
}
