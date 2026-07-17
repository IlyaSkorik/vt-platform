import { ClipboardList, Plus } from "lucide-react";
import { generatePath, Link } from "react-router";
import { applicationStatusPresentation, useMyApplications } from "@/entities/application";
import type { ApplicationSummaryResource } from "@/shared/api/generated/model-applications";
import { ROUTES } from "@/shared/config";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/ui";

function formatTotal(application: ApplicationSummaryResource): string {
  if (!application.totalAmount || !application.currency) {
    return "—";
  }
  return `${application.totalAmount} ${application.currency}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function ApplicationCard({
  application,
}: {
  application: ApplicationSummaryResource;
}): React.JSX.Element {
  const status = application.hasCorrections
    ? { label: "Требуется исправление", variant: "warning" as const }
    : applicationStatusPresentation(application.status);
  const detailTo = generatePath(ROUTES.cabinetApplication, { applicationId: application.id });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>
              #{application.id.slice(0, 8).toUpperCase()} от {formatDate(application.createdAt)}
            </CardTitle>
            <CardDescription>
              Выступлений: {application.submissionCount} · Сумма: {formatTotal(application)}
            </CardDescription>
          </div>
          <Badge variant={status.variant}>{status.label}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Button asChild variant="outline" size="sm">
          <Link to={detailTo}>Открыть</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function ApplicationList({
  applications,
}: {
  applications: ApplicationSummaryResource[];
}): React.JSX.Element {
  if (applications.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList />}
        title="Заявок пока нет"
        description="Выберите фестиваль в каталоге, чтобы подать первую заявку."
      />
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {applications.map((application) => (
        <ApplicationCard key={application.id} application={application} />
      ))}
    </div>
  );
}

export function MyApplicationsPage(): React.JSX.Element {
  const { data, isLoading } = useMyApplications();
  const applications = data ?? [];
  const drafts = applications.filter((application) => application.status === "DRAFT");

  return (
    <PageContainer>
      <PageHeader
        actions={
          <Button asChild size="sm">
            <Link to={ROUTES.cabinetCompetitions}>
              <Plus className="size-4" />
              Подать заявку
            </Link>
          </Button>
        }
      >
        <PageTitle>Мои заявки</PageTitle>
        <PageDescription>Заявки на фестивали и их статусы подачи.</PageDescription>
      </PageHeader>
      <PageContent>
        {isLoading ? (
          <LoadingState label="Загружаем заявки…" />
        ) : (
          <Tabs defaultValue="all">
            <TabsList>
              <TabsTrigger className="cursor-pointer" value="all">
                Все ({applications.length})
              </TabsTrigger>
              <TabsTrigger className="cursor-pointer" value="drafts">
                Черновики ({drafts.length})
              </TabsTrigger>
            </TabsList>
            <TabsContent value="all">
              <ApplicationList applications={applications} />
            </TabsContent>
            <TabsContent value="drafts">
              <ApplicationList applications={drafts} />
            </TabsContent>
          </Tabs>
        )}
      </PageContent>
    </PageContainer>
  );
}
