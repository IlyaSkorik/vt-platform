import {
  Award,
  CalendarDays,
  ClipboardList,
  FileText,
  Inbox,
  MailPlus,
  Medal,
  Plus,
  Wallet,
} from "lucide-react";
import { useMemo } from "react";
import { createSearchParams, Link } from "react-router";

import { type AuthModule, useAuth } from "@/app/providers";

import {
  competitionStatusLabel,
  competitionStatusVariant,
  useCompetitionsList,
} from "@/features/competitions";
import { ROLE_LABELS, useStaffInvitations } from "@/features/staff-invitations";
import { type OverviewApplication, useStaffOverview } from "@/features/staff-overview";
import { ROUTES } from "@/shared/config";
import {
  Alert,
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

/** How many rows a summary card shows before handing over to its section. */
const PREVIEW_LIMIT = 5;

/**
 * The queues the desk is actually worked from, in the order they are worked.
 *
 * The workspace computes counts for five; ARCHIVE (cancelled) is left off — it is
 * where things go to stop needing anybody, so a number on the front screen would
 * only compete for attention with the four that do.
 */
const WORKED_QUEUES: ReadonlyArray<{
  key: string;
  title: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
  tone: string;
}> = [
  {
    key: "NEW",
    title: "На доработке",
    hint: "Ждут решения организатора",
    icon: Inbox,
    tone: "bg-warning/10 text-warning",
  },
  {
    key: "WAITING_PAYMENT",
    title: "Ожидают оплату",
    hint: "Квитанция ещё не приложена",
    icon: Wallet,
    tone: "bg-warning/10 text-warning",
  },
  {
    key: "READY",
    title: "Готовы к фестивалю",
    hint: "Приняты и оплачены",
    icon: ClipboardList,
    tone: "bg-success/10 text-success",
  },
  {
    key: "RUNNING",
    title: "Назначены",
    hint: "Стоят в программе",
    icon: CalendarDays,
    tone: "bg-primary/10 text-primary",
  },
];

/**
 * The shortcuts on the front screen, each tied to the module it leads into.
 *
 * An action without a module is one every organization has. The rest disappear
 * with their section rather than leading to a page that would refuse them.
 */
const QUICK_ACTIONS: ReadonlyArray<{
  title: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  module?: AuthModule;
}> = [
  {
    title: "Новый фестиваль",
    to: ROUTES.staffCompetitionsNew,
    icon: Plus,
    module: "COMPETITIONS",
  },
  { title: "Пригласить сотрудника", to: ROUTES.staffInvitations, icon: MailPlus },
  { title: "Программа", to: ROUTES.staffProgram, icon: CalendarDays, module: "PROGRAMS" },
  { title: "Дипломы", to: ROUTES.staffDiplomas, icon: Award, module: "DIPLOMAS" },
  { title: "Финансы", to: ROUTES.staffFinance, icon: FileText, module: "FINANCE" },
];

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const at = new Date(iso);
  return Number.isNaN(at.getTime())
    ? "—"
    : at.toLocaleDateString("ru-RU", { day: "2-digit", month: "long" });
}

/** Deep-link into the workspace, already filtered to the queue that was clicked. */
function queueLink(key: string): string {
  return `${ROUTES.staffApplications}?${createSearchParams({ queue: key }).toString()}`;
}

/** Deep-link straight to one application's card in the workspace. */
function applicationLink(item: OverviewApplication): string {
  return `${ROUTES.staffApplications}?${createSearchParams({
    queue: item.queue,
    selected: item.id,
  }).toString()}`;
}

function QueueTile({
  title,
  hint,
  count,
  icon: Icon,
  tone,
  to,
  loading,
}: {
  title: string;
  hint: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  tone: string;
  to: string;
  loading: boolean;
}): React.JSX.Element {
  return (
    <Card className="shadow-none transition-colors hover:border-primary/40">
      <Link
        to={to}
        className="block rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardDescription>{title}</CardDescription>
              {loading ? (
                <Skeleton className="mt-2 h-8 w-12" />
              ) : (
                <CardTitle className="mt-2 text-2xl">{count}</CardTitle>
              )}
            </div>
            <div className={`flex size-9 items-center justify-center rounded-md ${tone}`}>
              <Icon className="size-4" aria-hidden="true" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">{hint}</p>
        </CardContent>
      </Link>
    </Card>
  );
}

/**
 * The organizer's home screen.
 *
 * What is on the desk right now, and one click to whichever part of it needs
 * somebody — rather than four cards reading "—" above a promise that the module
 * will be connected later.
 *
 * Everything here comes from the same workspace projection the applications screen
 * is built on, so a number on this page and the queue it opens can never disagree.
 */
export function StaffDashboardPage(): React.JSX.Element {
  // The summary only summarizes what the organization actually has. A section it
  // was not sold is not shown as empty or as failing — it is absent, and the read
  // behind it is never made, because the endpoint would refuse it anyway.
  const { hasModule } = useAuth();
  const showApplications = hasModule("APPLICATIONS");
  const showCompetitions = hasModule("COMPETITIONS");

  const overview = useStaffOverview({ enabled: showApplications });
  const competitions = useCompetitionsList({ enabled: showCompetitions });
  const invitations = useStaffInvitations();

  const counts = useMemo(() => {
    const map = new Map((overview.data?.queues ?? []).map((queue) => [queue.key, queue.count]));
    return (key: string) => map.get(key) ?? 0;
  }, [overview.data]);

  const recent = useMemo(
    () =>
      [...(overview.data?.applications ?? [])]
        .sort((a, b) => new Date(b.submissionDate).getTime() - new Date(a.submissionDate).getTime())
        .slice(0, PREVIEW_LIMIT),
    [overview.data],
  );

  const activeCompetitions = useMemo(
    () =>
      [...(competitions.data ?? [])]
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        .slice(0, PREVIEW_LIMIT),
    [competitions.data],
  );

  const pendingInvitations = useMemo(
    () =>
      (invitations.data ?? []).filter((item) => item.status === "pending").slice(0, PREVIEW_LIMIT),
    [invitations.data],
  );

  return (
    <PageContainer size="wide">
      <PageHeader
        actions={
          showCompetitions ? (
            <Button asChild size="sm">
              <Link to={ROUTES.staffCompetitionsNew}>
                <Plus className="size-4" />
                Новый фестиваль
              </Link>
            </Button>
          ) : null
        }
      >
        <PageTitle>Панель управления</PageTitle>
        <PageDescription>
          Что сейчас на столе: очередь заявок, фестивали и доступы команды.
        </PageDescription>
      </PageHeader>
      <PageContent className="flex flex-col gap-6">
        {showApplications && overview.isError ? (
          <Alert variant="danger">
            Не удалось загрузить очередь заявок. Обновите страницу или откройте раздел «Заявки».
          </Alert>
        ) : null}

        {showApplications ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {WORKED_QUEUES.map((queue) => (
              <QueueTile
                key={queue.key}
                title={queue.title}
                hint={queue.hint}
                count={counts(queue.key)}
                icon={queue.icon}
                tone={queue.tone}
                to={queueLink(queue.key)}
                loading={overview.isLoading}
              />
            ))}
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-2">
          {showApplications ? (
            <Card className="shadow-none">
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle>Последние заявки</CardTitle>
                  <CardDescription>Самые свежие поступления по всем фестивалям.</CardDescription>
                </div>
                <Button asChild variant="ghost" size="sm">
                  <Link to={ROUTES.staffApplications}>Все заявки</Link>
                </Button>
              </CardHeader>
              <CardContent className="py-0">
                {overview.isLoading ? (
                  <div className="flex flex-col gap-3 py-3">
                    <Skeleton className="h-12" />
                    <Skeleton className="h-12" />
                  </div>
                ) : recent.length === 0 ? (
                  <EmptyState
                    icon={<Inbox aria-hidden="true" />}
                    title="Заявок пока нет"
                    description="Как только участники начнут подавать заявки, они появятся здесь."
                  />
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {recent.map((item) => (
                      <li key={item.id}>
                        <Link
                          to={applicationLink(item)}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-md px-1 py-3 outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <span className="min-w-0">
                            <span className="block text-sm font-medium">
                              №{item.applicationNumber} · {item.competition}
                            </span>
                            <span className="mt-1 block text-xs text-muted-foreground">
                              {item.organization || "Без организации"} · выступлений:{" "}
                              {item.performancesCount} · {formatDate(item.submissionDate)}
                            </span>
                          </span>
                          {item.badges?.hasCorrections ? (
                            <Badge variant="warning">На исправлении</Badge>
                          ) : item.badges?.hasMissingFiles ? (
                            <Badge variant="warning">Нет файлов</Badge>
                          ) : (
                            <Badge variant="neutral">{item.status}</Badge>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ) : null}

          {showCompetitions ? (
            <Card className="shadow-none">
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle>Фестивали</CardTitle>
                  <CardDescription>Последние созданные и их состояние.</CardDescription>
                </div>
                <Button asChild variant="ghost" size="sm">
                  <Link to={ROUTES.staffCompetitions}>Все фестивали</Link>
                </Button>
              </CardHeader>
              <CardContent className="py-0">
                {competitions.isLoading ? (
                  <div className="flex flex-col gap-3 py-3">
                    <Skeleton className="h-12" />
                    <Skeleton className="h-12" />
                  </div>
                ) : activeCompetitions.length === 0 ? (
                  <EmptyState
                    icon={<Medal aria-hidden="true" />}
                    title="Фестивалей пока нет"
                    description="Создайте первый фестиваль, чтобы принимать заявки."
                  />
                ) : (
                  <ul className="flex flex-col divide-y divide-border">
                    {activeCompetitions.map((competition) => (
                      <li key={competition.id}>
                        <Link
                          to={`${ROUTES.staffCompetitions}/${competition.id}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-md px-1 py-3 outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <span className="min-w-0">
                            <span className="block text-sm font-medium">{competition.title}</span>
                            <span className="mt-1 block text-xs text-muted-foreground">
                              {competition.season}
                            </span>
                          </span>
                          <Badge variant={competitionStatusVariant(competition.status)}>
                            {competitionStatusLabel(competition.status)}
                          </Badge>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ) : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="shadow-none">
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <div>
                <CardTitle>Приглашения в команду</CardTitle>
                <CardDescription>Отправленные и ещё не принятые.</CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.staffInvitations}>Все приглашения</Link>
              </Button>
            </CardHeader>
            <CardContent className="py-0">
              {invitations.isLoading ? (
                <div className="flex flex-col gap-3 py-3">
                  <Skeleton className="h-12" />
                </div>
              ) : pendingInvitations.length === 0 ? (
                <EmptyState
                  icon={<MailPlus aria-hidden="true" />}
                  title="Непринятых приглашений нет"
                  description="Пригласите сотрудника, чтобы дать ему доступ к панели."
                />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {pendingInvitations.map((invitation) => (
                    <li
                      key={invitation.id}
                      className="flex flex-wrap items-center justify-between gap-2 px-1 py-3"
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{invitation.email}</span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          {ROLE_LABELS[invitation.role] ?? invitation.role} · до{" "}
                          {formatDate(invitation.expiresAt)}
                        </span>
                      </span>
                      <Badge variant="info">Ожидает</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-none">
            <CardHeader>
              <CardTitle>Быстрые действия</CardTitle>
              <CardDescription>Частые операции — без лишней навигации.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {QUICK_ACTIONS.filter(
                (action) => action.module === undefined || hasModule(action.module),
              ).map((action) => {
                const Icon = action.icon;
                return (
                  <Button key={action.to} asChild variant="outline" size="sm">
                    <Link to={action.to}>
                      <Icon className="size-4" />
                      {action.title}
                    </Link>
                  </Button>
                );
              })}
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </PageContainer>
  );
}
