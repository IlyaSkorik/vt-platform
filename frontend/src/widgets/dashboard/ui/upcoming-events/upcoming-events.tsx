import type { LucideIcon } from "lucide-react";
import { CalendarClock, CalendarDays, Gavel, Mic, Trophy } from "lucide-react";
import { Skeleton } from "@/shared/ui";
import { useUpcomingEvents } from "../../api";
import { deriveWidgetStatus } from "../../lib";
import type { EventKind, UpcomingEvent, WidgetStatus } from "../../model";
import { EVENT_KIND_LABELS, formatDate, formatRelativeTime } from "../../model";
import { WidgetCard } from "../widget-card";

/** Event kind → leading icon. */
const KIND_ICON: Record<EventKind, LucideIcon> = {
  submission_deadline: CalendarClock,
  judging_start: Gavel,
  results: Trophy,
  live_slot: Mic,
  reminder: CalendarDays,
};

function EventsSkeleton(): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-3">
      {[0, 1, 2].map((i) => (
        <li key={i} className="flex items-center gap-3">
          <Skeleton className="size-9 rounded-md" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-3/5" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function EventRow({ event }: { event: UpcomingEvent }): React.JSX.Element {
  const Icon = KIND_ICON[event.kind];
  return (
    <li className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
      <span
        aria-hidden="true"
        className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary [&_svg]:size-4"
      >
        <Icon />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-medium text-foreground text-sm">{event.title}</span>
        <span className="truncate text-muted-foreground text-xs">
          {event.competitionTitle} · {EVENT_KIND_LABELS[event.kind]}
        </span>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <time
          dateTime={event.startsAt}
          className="font-medium text-foreground text-xs tabular-nums"
        >
          {formatDate(event.startsAt)}
        </time>
        <span className="text-muted-foreground text-xs">{formatRelativeTime(event.startsAt)}</span>
      </div>
    </li>
  );
}

export interface UpcomingEventsViewProps {
  status: WidgetStatus;
  events: readonly UpcomingEvent[];
  onRetry?: () => void;
}

/** Presentational view — pure over its props for stories/tests. */
export function UpcomingEventsView({
  status,
  events,
  onRetry,
}: UpcomingEventsViewProps): React.JSX.Element {
  return (
    <WidgetCard
      title="Ближайшие события"
      status={status}
      loadingSkeleton={<EventsSkeleton />}
      emptyIcon={<CalendarDays />}
      emptyTitle="Нет событий"
      emptyDescription="Запланированные события появятся здесь."
      {...(onRetry ? { onRetry } : {})}
    >
      <ul className="flex flex-col divide-y divide-border">
        {events.map((event) => (
          <EventRow key={event.id} event={event} />
        ))}
      </ul>
    </WidgetCard>
  );
}

/**
 * UpcomingEvents — scheduled milestones (deadlines, judging starts, result
 * publications, live slots) ordered by proximity, wired to
 * {@link useUpcomingEvents}. Shows both an absolute date and a relative hint.
 */
export function UpcomingEvents(): React.JSX.Element {
  const query = useUpcomingEvents();
  const events = query.data ?? [];
  const status = deriveWidgetStatus(query, events.length === 0);

  return <UpcomingEventsView status={status} events={events} onRetry={() => query.refetch()} />;
}
