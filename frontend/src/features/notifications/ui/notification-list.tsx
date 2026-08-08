import { Bell } from "lucide-react";
import { useNavigate } from "react-router";

import type { Notification } from "@/shared/api/generated/model-notifications";
import { cn } from "@/shared/lib";
import { EmptyState } from "@/shared/ui";

import { useMarkNotificationRead } from "../api/hooks";
import { formatNotificationTime, notificationPresentation } from "../lib/presentation";

/**
 * The feed itself — one row per notice, shared by the notifications page and the
 * dashboard's short list.
 *
 * A row with a `link` is a button: opening it marks the notice read and goes where
 * the notice is about, which is the only thing anyone wants to do with "нужно
 * исправить". A row without one is inert text, not a dead control.
 */
export function NotificationList({
  items,
  emptyDescription = "Когда появятся события по вашим заявкам или документам, они будут здесь.",
}: {
  items: Notification[];
  emptyDescription?: string;
}): React.JSX.Element {
  const navigate = useNavigate();
  const markRead = useMarkNotificationRead();

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Bell aria-hidden="true" />}
        title="Новых уведомлений нет"
        description={emptyDescription}
      />
    );
  }

  const open = (item: Notification): void => {
    if (item.readAt === null) {
      markRead.mutate(item.id);
    }
    if (item.link) {
      void navigate(item.link);
    }
  };

  return (
    <ul className="flex flex-col divide-y divide-border">
      {items.map((item) => {
        const { label, icon: Icon, tone } = notificationPresentation(item.kind);
        const unread = item.readAt === null;
        const actionable = Boolean(item.link) || unread;
        const Row = actionable ? "button" : "div";
        return (
          <li key={item.id}>
            <Row
              {...(actionable ? { type: "button" as const, onClick: () => open(item) } : {})}
              className={cn(
                "flex w-full items-start gap-3 px-1 py-3 text-left",
                actionable && "cursor-pointer hover:bg-muted/40",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md",
                  tone,
                )}
              >
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className={cn("text-sm", unread ? "font-semibold" : "font-medium")}>
                    {item.title}
                  </span>
                  {/* Spelled out, not just coloured: an unread dot alone is invisible
                      to a screen reader and to anyone who cannot tell the tones apart. */}
                  {unread ? (
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                      Новое
                    </span>
                  ) : null}
                </span>
                {item.body ? (
                  <span className="mt-1 block whitespace-pre-line text-sm text-muted-foreground">
                    {item.body}
                  </span>
                ) : null}
                <span className="mt-1 block text-xs text-muted-foreground">
                  {label} · {formatNotificationTime(item.createdAt)}
                </span>
              </span>
            </Row>
          </li>
        );
      })}
    </ul>
  );
}
