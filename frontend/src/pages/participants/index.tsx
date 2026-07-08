import {
  Card,
  CardContent,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

/**
 * Participants page (placeholder).
 *
 * Renders inside the Application Shell using the page primitives. The
 * participants table (TanStack Table) and management flows are delivered by
 * the Participants feature. Minor PII is never listed by identity —
 * participants are addressed by opaque ids (API-000 §10.3).
 */
export function ParticipantsPage(): React.JSX.Element {
  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Участники</PageTitle>
        <PageDescription>Список участников и управление ими.</PageDescription>
      </PageHeader>
      <PageContent>
        <Card>
          <CardContent className="pt-6 text-muted-foreground text-sm">
            Таблица участников появится здесь.
          </CardContent>
        </Card>
      </PageContent>
    </PageContainer>
  );
}
