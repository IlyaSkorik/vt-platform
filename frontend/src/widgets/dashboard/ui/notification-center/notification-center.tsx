import type { LucideIcon } from "lucide-react";
import { Bell, CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/shared/lib";
import { Badge, Skeleton } from "@/shared/ui";
import { useNotifications } from "../../api";
import { deriveWidgetStatus } from "../../lib";
import type { NotificationItem, NotificationKind, WidgetStatus } from "../../model";
import { formatRelativeTime } from "../../model";
import { WidgetCard } from "../widget-card";

/** Notification kind → icon + tint (semantic status tokens only). */
const KIND_STYLE: Record<NotificationKind, { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: "bg-info-surface text-info" },
  success: { icon: CircleCheck, className: "bg-success-surface text-success" },
  warning: { icon: TriangleAlert, className: "bg-warning-surface text-warning" },
  danger: { icon: CircleAlert, className: "bg-danger-surface text-danger" },
};

function NotificationsSkeleton(): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-3">
      {[0, 1, 2].map((i) => (
        <li key={i} className="flex gap-3">
          <Skeleton variant="circle" className="size-8 shrink-0" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-4/5" />
          </div>
        </li>
      ))}
    </ul>
  );
}

function NotificationRow({ notification }: { notification: NotificationItem }): React.JSX.Element {
  const style = KIND_STYLE[notification.kind];
  const Icon = style.icon;
  return (
    <li
      className={cn(
        "flex gap-3 rounded-md py-2 pl-2 pr-1 first:pt-0",
        !notification.read && "bg-accent/40",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full [&_svg]:size-4",
          style.className,
        )}
      >
        <Icon />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="truncate font-medium text-foreground text-sm">{notification.title}</span>
          {!notification.read && (
            <span
              role="status"
              aria-label="Не прочитано"
              className="size-1.5 shrink-0 rounded-full bg-primary"
            />
          )}
        </div>
        <span className="text-muted-foreground text-xs">{notification.body}</span>
        <time
          dateTime={notification.createdAt}
          className="text-muted-foreground text-xs tabular-nums"
        >
          {formatRelativeTime(notification.createdAt)}
        </time>
      </div>
    </li>
  );
}

export interface NotificationCenterViewProps {
  status: WidgetStatus;
  notifications: readonly NotificationItem[];
  onRetry?: () => void;
}

/** Presentational view — pure over its props for stories/tests. */
export function NotificationCenterView({
  status,
  notifications,
  onRetry,
}: NotificationCenterViewProps): React.JSX.Element {
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <WidgetCard
      title="Уведомления"
      status={status}
      loadingSkeleton={<NotificationsSkeleton />}
      emptyIcon={<Bell />}
      emptyTitle="Нет уведомлений"
      emptyDescription="Здесь появятся новые уведомления."
      {...(onRetry ? { onRetry } : {})}
      headerAction={
        unread > 0 ? (
          <Badge variant="primary" size="sm" aria-label={`${unread} непрочитанных`}>
            {unread}
          </Badge>
        ) : undefined
      }
    >
      <ul className="flex flex-col gap-1">
        {notifications.map((notification) => (
          <NotificationRow key={notification.id} notification={notification} />
        ))}
      </ul>
    </WidgetCard>
  );
}

/**
 * NotificationCenter — the notification feed with an unread count badge, wired
 * to {@link useNotifications}. Unread items are visually distinguished and
 * carry an accessible marker so the state is not colour-only (WCAG 2.1 AA).
 */
export function NotificationCenter(): React.JSX.Element {
  const query = useNotifications();
  const notifications = query.data ?? [];
  const status = deriveWidgetStatus(query, notifications.length === 0);

  return (
    <NotificationCenterView
      status={status}
      notifications={notifications}
      onRetry={() => query.refetch()}
    />
  );
}
