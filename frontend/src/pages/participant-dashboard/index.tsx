import { Bell, ClipboardList, FileText, Medal, Users } from "lucide-react";

import { useAuth } from "@/app/providers";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

const personalCards = [
  {
    title: "Ближайшие конкурсы",
    description: "Подходящие события появятся здесь после подключения конкурсного модуля.",
    icon: Medal,
  },
  {
    title: "Мои участники",
    description: "Профили участников будут доступны в личном кабинете.",
    icon: Users,
  },
  {
    title: "Мои заявки",
    description: "Статусы поданных заявок будут собраны в одном месте.",
    icon: ClipboardList,
  },
  {
    title: "Документы",
    description: "Личные файлы и подтверждения появятся после запуска раздела.",
    icon: FileText,
  },
];

export function ParticipantDashboardPage(): React.JSX.Element {
  const { user } = useAuth();
  const firstName = user?.displayName?.split(" ")[0] ?? "Здравствуйте";

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>{firstName}, добро пожаловать</PageTitle>
        <PageDescription>
          Личный кабинет собирает ваши конкурсы, участников, заявки и уведомления без
          административных данных.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {personalCards.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title} className="shadow-none">
                <CardHeader className="gap-3">
                  <div className="flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Icon className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{item.title}</CardTitle>
                    <CardDescription>{item.description}</CardDescription>
                  </div>
                </CardHeader>
              </Card>
            );
          })}
        </div>
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>Уведомления</CardTitle>
            <CardDescription>Только личные события аккаунта и заявок.</CardDescription>
          </CardHeader>
          <CardContent>
            <EmptyState
              icon={<Bell aria-hidden="true" />}
              title="Новых уведомлений нет"
              description="Когда появятся события по вашим заявкам или документам, они будут здесь."
            />
          </CardContent>
        </Card>
      </PageContent>
    </PageContainer>
  );
}
