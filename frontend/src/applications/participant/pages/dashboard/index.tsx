import { AlertTriangle, ClipboardList, FileText, Medal, Plus, Users } from "lucide-react";
import { useMemo } from "react";
import { generatePath, Link } from "react-router";

import { useAuth } from "@/app/providers";
import { applicationStatusPresentation, useMyApplications } from "@/entities/application";
import { useParticipants } from "@/entities/participant";
import { formatDeadline, selectUpcoming, usePublicFestivals } from "@/features/festival-catalog";
import { useMyDocuments } from "@/features/my-documents";
import { NotificationList, useNotificationFeed } from "@/features/notifications";
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
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Skeleton,
} from "@/shared/ui";

/** How many notices and festivals the summary shows before sending you to the section. */
const PREVIEW_LIMIT = 4;

/**
 * Order statuses that still owe the applicant an action, in the order the tile
 * should mention them. A submitted-and-unpaid order is the one people forget.
 */
function needsAttention(application: ApplicationSummaryResource): boolean {
  return application.hasCorrections || application.status === "WAITING_PAYMENT";
}

function StatTile({
  title,
  value,
  hint,
  icon: Icon,
  to,
  loading,
  tone = "text-primary bg-primary/10",
}: {
  title: string;
  value: number;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
  to: string;
  loading: boolean;
  tone?: string | undefined;
}): React.JSX.Element {
  return (
    <Card className="shadow-none transition-colors hover:border-primary/40">
      <Link
        to={to}
        className="block rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <CardHeader className="gap-3">
          <div className={`flex size-9 items-center justify-center rounded-md ${tone}`}>
            <Icon className="size-4" aria-hidden="true" />
          </div>
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            {loading ? (
              <Skeleton className="mt-1 h-7 w-12" />
            ) : (
              <p className="mt-1 font-semibold text-2xl leading-none">{value}</p>
            )}
            <CardDescription className="mt-1">{hint}</CardDescription>
          </div>
        </CardHeader>
      </Link>
    </Card>
  );
}

/**
 * The cabinet's home screen.
 *
 * A summary of what this account actually has and what it still owes, rather than
 * a description of what the cabinet will eventually contain. Every tile is a link:
 * the point of a dashboard is to get somebody to the thing that needs them, and the
 * number is only there to say whether it is worth going.
 */
export function ParticipantDashboardPage(): React.JSX.Element {
  const { user } = useAuth();
  const firstName = user?.displayName?.split(" ")[0] ?? "Здравствуйте";

  const applications = useMyApplications();
  const participants = useParticipants();
  const documents = useMyDocuments();
  const festivals = usePublicFestivals();
  const notifications = useNotificationFeed();

  const applicationList = useMemo(() => applications.data ?? [], [applications.data]);
  const attention = useMemo(() => applicationList.filter(needsAttention), [applicationList]);
  const upcoming = useMemo(
    () => selectUpcoming(festivals.data ?? [], null, PREVIEW_LIMIT),
    [festivals.data],
  );

  return (
    <PageContainer size="wide">
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
        <PageTitle>{firstName}, добро пожаловать</PageTitle>
        <PageDescription>
          Ваши фестивали, участники, заявки и уведомления — без административных данных.
        </PageDescription>
      </PageHeader>
      <PageContent className="flex flex-col gap-6">
        {/* What still needs doing, before anything else on the screen. An order
            waiting on a receipt or a correction is the only thing here with a
            deadline attached to it. */}
        {attention.length > 0 ? (
          <Card className="border-warning/40 bg-warning/5 shadow-none">
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-warning/10 text-warning">
                  <AlertTriangle className="size-4" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle className="text-base">Требуют вашего внимания</CardTitle>
                  <CardDescription>
                    Заявки, по которым организатор ждёт действия с вашей стороны.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {attention.map((application) => {
                const status = application.hasCorrections
                  ? { label: "Требуется исправление", variant: "warning" as const }
                  : applicationStatusPresentation(application.status);
                return (
                  <Link
                    key={application.id}
                    to={generatePath(ROUTES.cabinetApplication, { applicationId: application.id })}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md px-1 py-2 outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="text-sm font-medium">
                      Заявка №{application.id.slice(0, 8).toUpperCase()}
                    </span>
                    <Badge variant={status.variant}>{status.label}</Badge>
                  </Link>
                );
              })}
            </CardContent>
          </Card>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatTile
            title="Ближайшие фестивали"
            value={upcoming.length}
            hint="Открыт приём или скоро откроется"
            icon={Medal}
            to={ROUTES.cabinetCompetitions}
            loading={festivals.isLoading}
          />
          <StatTile
            title="Мои участники"
            value={participants.data?.length ?? 0}
            hint="Профили, привязанные к аккаунту"
            icon={Users}
            to={ROUTES.cabinetParticipants}
            loading={participants.isLoading}
          />
          <StatTile
            title="Мои заявки"
            value={applicationList.length}
            hint={
              attention.length > 0
                ? `Требуют внимания: ${attention.length}`
                : "Все заявки в работе и в архиве"
            }
            icon={ClipboardList}
            to={ROUTES.cabinetApplications}
            loading={applications.isLoading}
            tone={attention.length > 0 ? "text-warning bg-warning/10" : undefined}
          />
          <StatTile
            title="Документы"
            value={documents.data?.length ?? 0}
            hint="Дипломы и благодарственные письма"
            icon={FileText}
            to={ROUTES.cabinetDocuments}
            loading={documents.isLoading}
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="shadow-none">
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <div>
                <CardTitle>Уведомления</CardTitle>
                <CardDescription>Только личные события аккаунта и заявок.</CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.cabinetNotifications}>Все</Link>
              </Button>
            </CardHeader>
            <CardContent className="py-0">
              {notifications.isLoading ? (
                <div className="flex flex-col gap-3 py-3">
                  <Skeleton className="h-12" />
                  <Skeleton className="h-12" />
                </div>
              ) : (
                <NotificationList
                  items={(notifications.data?.items ?? []).slice(0, PREVIEW_LIMIT)}
                />
              )}
            </CardContent>
          </Card>

          <Card className="shadow-none">
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <div>
                <CardTitle>Ближайшие фестивали</CardTitle>
                <CardDescription>Куда можно подать заявку прямо сейчас.</CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.cabinetCompetitions}>Каталог</Link>
              </Button>
            </CardHeader>
            <CardContent className="py-0">
              {festivals.isLoading ? (
                <div className="flex flex-col gap-3 py-3">
                  <Skeleton className="h-12" />
                  <Skeleton className="h-12" />
                </div>
              ) : upcoming.length === 0 ? (
                <EmptyState
                  icon={<Medal aria-hidden="true" />}
                  title="Пока нет открытых фестивалей"
                  description="Как только приём заявок откроется, фестивали появятся здесь."
                />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {upcoming.map((festival) => (
                    <li key={festival.id}>
                      <Link
                        to={generatePath(ROUTES.cabinetFestival, {
                          festivalId: festival.slug ?? festival.id,
                        })}
                        className="block rounded-md px-1 py-3 outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <span className="block text-sm font-medium">{festival.title}</span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {formatDeadline(festival) ?? "Сроки уточняются"}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </PageContainer>
  );
}
