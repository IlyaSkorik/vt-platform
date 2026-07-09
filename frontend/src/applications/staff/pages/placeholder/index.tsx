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

type WorkspacePlaceholderPageProps = {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
};

export function WorkspacePlaceholderPage({
  title,
  description,
  icon: Icon,
}: WorkspacePlaceholderPageProps): React.JSX.Element {
  const emptyTitle = "Раздел панели готов";

  return (
    <PageContainer>
      <PageHeader>
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <Icon className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <PageTitle>{title}</PageTitle>
            <PageDescription>{description}</PageDescription>
          </div>
        </div>
      </PageHeader>
      <PageContent>
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>
            <EmptyState
              icon={<Icon aria-hidden="true" />}
              title={emptyTitle}
              description="Бизнес-модуль ещё не реализован. Маршрут, layout, навигация и пустое состояние уже подключены."
            />
          </CardContent>
        </Card>
      </PageContent>
    </PageContainer>
  );
}
