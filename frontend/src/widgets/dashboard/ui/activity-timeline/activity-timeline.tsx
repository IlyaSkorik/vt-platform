import type { LucideIcon } from "lucide-react";
import {
  Award,
  CheckCircle2,
  CreditCard,
  FileCheck,
  FileUp,
  Gavel,
  Megaphone,
  Send,
} from "lucide-react";
import { Skeleton } from "@/shared/ui";
import { useActivityFeed } from "../../api";
import { deriveWidgetStatus } from "../../lib";
import type { ActivityEvent, ActivityKind, WidgetStatus } from "../../model";
import { formatRelativeTime } from "../../model";
import { WidgetCard } from "../widget-card";

/** Domain-event kind → icon, tint and a Russian past-tense verb phrase. */
const ACTIVITY_META: Record<ActivityKind, { icon: LucideIcon; className: string; verb: string }> = {
  application_submitted: {
    icon: Send,
    className: "bg-info-surface text-info",
    verb: "подал заявку",
  },
  application_accepted: {
    icon: CheckCircle2,
    className: "bg-success-surface text-success",
    verb: "заявка принята",
  },
  performance_uploaded: {
    icon: FileUp,
    className: "bg-info-surface text-info",
    verb: "загрузил работу",
  },
  scorecard_submitted: {
    icon: Gavel,
    className: "bg-warning-surface text-warning",
    verb: "оценка выставлена",
  },
  result_published: {
    icon: Award,
    className: "bg-success-surface text-success",
    verb: "результаты опубликованы",
  },
  diploma_issued: {
    icon: FileCheck,
    className: "bg-success-surface text-success",
    verb: "диплом выдан",
  },
  payment_captured: {
    icon: CreditCard,
    className: "bg-muted text-muted-foreground",
    verb: "оплата получена",
  },
  competition_published: {
    icon: Megaphone,
    className: "bg-info-surface text-info",
    verb: "фестиваль опубликован",
  },
};

function TimelineSkeleton(): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-4">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="flex gap-3">
          <Skeleton variant="circle" className="size-7 shrink-0" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5 pt-0.5">
            <Skeleton className="h-4 w-3/5" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function TimelineItem({
  event,
  isLast,
}: {
  event: ActivityEvent;
  isLast: boolean;
}): React.JSX.Element {
  const meta = ACTIVITY_META[event.kind];
  const Icon = meta.icon;
  return (
    <li className="flex gap-3">
      <div className="flex flex-col items-center">
        <span
          aria-hidden="true"
          className={`flex size-7 shrink-0 items-center justify-center rounded-full [&_svg]:size-3.5 ${meta.className}`}
        >
          <Icon />
        </span>
        {!isLast && <span aria-hidden="true" className="w-px flex-1 bg-border" />}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 pb-4">
        <p className="text-foreground text-sm">
          <span className="font-medium">{event.subject}</span>{" "}
          <span className="text-muted-foreground">— {meta.verb}</span>
        </p>
        <time dateTime={event.occurredAt} className="text-muted-foreground text-xs tabular-nums">
          {formatRelativeTime(event.occurredAt)}
        </time>
      </div>
    </li>
  );
}

export interface ActivityTimelineViewProps {
  status: WidgetStatus;
  events: readonly ActivityEvent[];
  onRetry?: () => void;
}

/** Presentational view — pure over its props for stories/tests. */
export function ActivityTimelineView({
  status,
  events,
  onRetry,
}: ActivityTimelineViewProps): React.JSX.Element {
  return (
    <WidgetCard
      title="Лента активности"
      status={status}
      loadingSkeleton={<TimelineSkeleton />}
      emptyTitle="Пока нет активности"
      emptyDescription="Последние события платформы появятся здесь."
      {...(onRetry ? { onRetry } : {})}
    >
      <ul className="flex flex-col">
        {events.map((event, index) => (
          <TimelineItem key={event.id} event={event} isLast={index === events.length - 1} />
        ))}
      </ul>
    </WidgetCard>
  );
}

/**
 * ActivityTimeline — a chronological feed of recent platform domain events
 * (submissions, judging, results, diplomas, payments), wired to
 * {@link useActivityFeed}. Renders a connected timeline rail with per-event
 * icons; token-only.
 */
export function ActivityTimeline(): React.JSX.Element {
  const query = useActivityFeed();
  const events = query.data ?? [];
  const status = deriveWidgetStatus(query, events.length === 0);

  return <ActivityTimelineView status={status} events={events} onRetry={() => query.refetch()} />;
}
