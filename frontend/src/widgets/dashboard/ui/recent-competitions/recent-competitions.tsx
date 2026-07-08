import { Trophy } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Badge, Button, Skeleton } from "@/shared/ui";
import { useRecentCompetitions } from "../../api";
import { deriveWidgetStatus } from "../../lib";
import type { CompetitionSummary, WidgetStatus } from "../../model";
import { COMPETITION_STATUS, formatDate, formatNumber } from "../../model";
import { WidgetCard } from "../widget-card";

/** Loading placeholder mirroring the row layout so there's no reflow. */
function CompetitionsSkeleton(): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-3">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-4 w-3/5" />
            <Skeleton className="h-3 w-2/5" />
          </div>
          <Skeleton className="h-5 w-20 rounded-full" />
        </li>
      ))}
    </ul>
  );
}

function CompetitionRow({ competition }: { competition: CompetitionSummary }): React.JSX.Element {
  const presentation = COMPETITION_STATUS[competition.status];
  return (
    <li className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate font-medium text-foreground text-sm">{competition.title}</span>
        <span className="text-muted-foreground text-xs">
          {formatNumber(competition.applicationCount)} заявок · до{" "}
          {formatDate(competition.closesAt)}
        </span>
      </div>
      <Badge variant={presentation.variant} size="sm" className="shrink-0">
        {presentation.label}
      </Badge>
    </li>
  );
}

export interface RecentCompetitionsViewProps {
  status: WidgetStatus;
  competitions: readonly CompetitionSummary[];
  onRetry?: () => void;
}

/**
 * Presentational view — pure over its props, so every state (loading / empty /
 * error / success) is directly storyable and testable without a query client.
 */
export function RecentCompetitionsView({
  status,
  competitions,
  onRetry,
}: RecentCompetitionsViewProps): React.JSX.Element {
  return (
    <WidgetCard
      title="Последние конкурсы"
      status={status}
      loadingSkeleton={<CompetitionsSkeleton />}
      emptyIcon={<Trophy />}
      emptyTitle="Нет конкурсов"
      emptyDescription="Созданные конкурсы появятся здесь."
      {...(onRetry ? { onRetry } : {})}
      headerAction={
        <Button asChild variant="ghost" size="sm">
          <Link to={ROUTES.competitions}>Все конкурсы</Link>
        </Button>
      }
    >
      <ul className="flex flex-col divide-y divide-border">
        {competitions.map((competition) => (
          <CompetitionRow key={competition.id} competition={competition} />
        ))}
      </ul>
    </WidgetCard>
  );
}

/**
 * RecentCompetitions — the latest competitions with lifecycle status,
 * application counts and close dates, wired to {@link useRecentCompetitions}.
 */
export function RecentCompetitions(): React.JSX.Element {
  const query = useRecentCompetitions();
  const competitions = query.data ?? [];
  const status = deriveWidgetStatus(query, competitions.length === 0);

  return (
    <RecentCompetitionsView
      status={status}
      competitions={competitions}
      onRetry={() => query.refetch()}
    />
  );
}
