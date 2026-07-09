import { CalendarDays, ClipboardList, MailPlus, Medal, UserCheck, Users } from "lucide-react";

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

const operationalCards = [
  {
    title: "Заявки на проверке",
    value: "—",
    description: "Очередь появится после запуска модуля заявок.",
    icon: ClipboardList,
  },
  {
    title: "Ближайшие конкурсы",
    value: "—",
    description: "План событий подключается отдельным модулем.",
    icon: Medal,
  },
  {
    title: "Жюри онлайн",
    value: "—",
    description: "Статусы судей будут доступны после интеграции.",
    icon: UserCheck,
  },
  {
    title: "Сегодня в расписании",
    value: "—",
    description: "Расписание не показывает выдуманные данные.",
    icon: CalendarDays,
  },
];

export function StaffDashboardPage(): React.JSX.Element {
  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Панель управления</PageTitle>
        <PageDescription>
          Операционное пространство организации: заявки, конкурсы, расписание, команда и доступы.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {operationalCards.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title} className="shadow-none">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardDescription>{item.title}</CardDescription>
                      <CardTitle className="mt-2 text-2xl">{item.value}</CardTitle>
                    </div>
                    <div className="flex size-9 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Icon className="size-4" aria-hidden="true" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">{item.description}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle>Последние приглашения</CardTitle>
              <CardDescription>
                Реальные приглашения появятся после подключения раздела.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={<MailPlus aria-hidden="true" />}
                title="Приглашений пока нет"
                description="Здесь будет видна недавняя активность по доступам сотрудников."
              />
            </CardContent>
          </Card>
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle>Быстрые действия</CardTitle>
              <CardDescription>Операционные команды без имитации бизнес-данных.</CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={<Users aria-hidden="true" />}
                title="Действия появятся вместе с модулями"
                description="Пока фундамент готовит место для будущих рабочих сценариев."
              />
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </PageContainer>
  );
}
