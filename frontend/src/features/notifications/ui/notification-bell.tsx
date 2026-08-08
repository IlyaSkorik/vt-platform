import { Bell } from "lucide-react";
import { Link } from "react-router";

import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

import { useNotificationFeed } from "../api/hooks";

/**
 * The cabinet shell's bell: a link to the notification section, badged when
 * something is unread.
 *
 * The count is part of the accessible label rather than only the badge — a number
 * floating over an icon is not something a screen reader announces, and "Уведомления"
 * alone would not say there is anything to see.
 *
 * A `Button asChild` rather than an `IconButton`: `IconButton` renders its icon
 * *beside* its children, and `asChild` needs exactly one child to graft onto.
 */
export function NotificationBell(): React.JSX.Element {
  const { data } = useNotificationFeed();
  const unread = data?.unreadCount ?? 0;

  return (
    <span className="relative inline-flex">
      <Button
        asChild
        iconOnly
        variant="ghost"
        size="sm"
        aria-label={unread > 0 ? `Уведомления, непрочитанных: ${unread}` : "Уведомления"}
      >
        <Link to={ROUTES.cabinetNotifications}>
          <Bell aria-hidden="true" />
        </Link>
      </Button>
      {unread > 0 ? (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-4 text-white"
        >
          {unread > 99 ? "99+" : unread}
        </span>
      ) : null}
    </span>
  );
}
