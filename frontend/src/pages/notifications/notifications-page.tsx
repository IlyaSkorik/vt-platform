import { CheckCheck } from "lucide-react";

import {
  NotificationList,
  useMarkAllNotificationsRead,
  useNotificationFeed,
} from "@/features/notifications";
import {
  Alert,
  Button,
  Card,
  CardContent,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

/**
 * The cabinet's notification section.
 *
 * Everything the platform has told this account, in one place. It exists because
 * every one of these notices is also an email, and email is the channel that gets
 * filtered, missed, or sent to an address somebody stopped reading — this is where
 * they look when they suspect they missed something.
 */
export function NotificationsPage(): React.JSX.Element {
  const { data, isLoading, isError } = useNotificationFeed();
  const markAll = useMarkAllNotificationsRead();
  const items = data?.items ?? [];
  const unread = data?.unreadCount ?? 0;

  return (
    <PageContainer>
      <PageHeader
        actions={
          unread > 0 ? (
            <Button
              variant="secondary"
              size="sm"
              loading={markAll.isPending}
              onClick={() => markAll.mutate()}
            >
              <CheckCheck className="size-4" />
              Прочитать все
            </Button>
          ) : null
        }
      >
        <PageTitle>Уведомления</PageTitle>
        <PageDescription>
          {unread > 0
            ? `Непрочитанных: ${unread}. События по вашим заявкам, оплате и результатам.`
            : "События по вашим заявкам, оплате и результатам."}
        </PageDescription>
      </PageHeader>
      <PageContent>
        {isLoading ? (
          <LoadingState label="Загружаем уведомления…" />
        ) : isError ? (
          <Alert variant="danger">
            Не удалось загрузить уведомления. Обновите страницу или попробуйте позже.
          </Alert>
        ) : (
          <Card>
            <CardContent className="py-2">
              <NotificationList items={items} />
            </CardContent>
          </Card>
        )}
      </PageContent>
    </PageContainer>
  );
}
