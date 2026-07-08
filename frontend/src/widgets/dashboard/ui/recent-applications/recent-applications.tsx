import { ClipboardList } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Avatar, Badge, Button, Skeleton } from "@/shared/ui";
import { useRecentApplications } from "../../api";
import { deriveWidgetStatus } from "../../lib";
import type { ApplicationSummary, WidgetStatus } from "../../model";
import { APPLICATION_STATUS, formatRelativeTime } from "../../model";
import { WidgetCard } from "../widget-card";

function ApplicationsSkeleton(): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-3">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="flex items-center gap-3">
          <Skeleton variant="circle" className="size-8" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-4 w-2/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
          <Skeleton className="h-5 w-24 rounded-full" />
        </li>
      ))}
    </ul>
  );
}

/** Two-letter initials from a pseudonymized alias (e.g. "Участник #A19F" → "#A"). */
function aliasInitials(alias: string): string {
  const token = alias.split("#")[1];
  return token ? `#${token.charAt(0)}` : alias.slice(0, 2).toUpperCase();
}

function ApplicationRow({ application }: { application: ApplicationSummary }): React.JSX.Element {
  const presentation = APPLICATION_STATUS[application.status];
  return (
    <li className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
      <Avatar size="sm" fallback={aliasInitials(application.participantAlias)} />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-medium text-foreground text-sm">
          {application.participantAlias}
        </span>
        <span className="truncate text-muted-foreground text-xs">
          {application.competitionTitle} · {application.nomination}
        </span>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <Badge variant={presentation.variant} size="sm">
          {presentation.label}
        </Badge>
        <time
          dateTime={application.submittedAt}
          className="text-muted-foreground text-xs tabular-nums"
        >
          {formatRelativeTime(application.submittedAt)}
        </time>
      </div>
    </li>
  );
}

export interface RecentApplicationsViewProps {
  status: WidgetStatus;
  applications: readonly ApplicationSummary[];
  onRetry?: () => void;
}

/** Presentational view — pure over its props for stories/tests. */
export function RecentApplicationsView({
  status,
  applications,
  onRetry,
}: RecentApplicationsViewProps): React.JSX.Element {
  return (
    <WidgetCard
      title="Последние заявки"
      status={status}
      loadingSkeleton={<ApplicationsSkeleton />}
      emptyIcon={<ClipboardList />}
      emptyTitle="Нет заявок"
      emptyDescription="Поданные заявки появятся здесь."
      {...(onRetry ? { onRetry } : {})}
      headerAction={
        <Button asChild variant="ghost" size="sm">
          <Link to={ROUTES.applications}>Все заявки</Link>
        </Button>
      }
    >
      <ul className="flex flex-col divide-y divide-border">
        {applications.map((application) => (
          <ApplicationRow key={application.id} application={application} />
        ))}
      </ul>
    </WidgetCard>
  );
}

/**
 * RecentApplications — the latest applications by pseudonymized alias, their
 * nomination and review status, wired to {@link useRecentApplications}.
 * Participants are addressed by opaque alias only — never real PII.
 */
export function RecentApplications(): React.JSX.Element {
  const query = useRecentApplications();
  const applications = query.data ?? [];
  const status = deriveWidgetStatus(query, applications.length === 0);

  return (
    <RecentApplicationsView
      status={status}
      applications={applications}
      onRetry={() => query.refetch()}
    />
  );
}
