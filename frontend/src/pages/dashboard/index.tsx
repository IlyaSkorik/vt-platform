import {
  Card,
  CardContent,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
} from "@/shared/ui";

/**
 * Dashboard page (placeholder).
 *
 * Renders inside the Application Shell using the page primitives. Real widgets
 * (competition progress, submissions, judging status) are composed here once
 * those features exist (bootstrap scope: layout skeleton only).
 */
export function DashboardPage(): React.JSX.Element {
  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Панель</PageTitle>
        <PageDescription>Обзор вашей активности на платформе.</PageDescription>
      </PageHeader>
      <PageContent>
        <PageSection>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {["Конкурсы", "Заявки", "Судейство"].map((title) => (
              <Card key={title} aria-label={title}>
                <CardContent className="pt-6">
                  <h2 className="font-medium text-sm">{title}</h2>
                  <p className="mt-2 text-muted-foreground text-sm">Данные появятся здесь.</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}
