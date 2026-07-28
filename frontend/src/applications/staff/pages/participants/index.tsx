import { Building2, ExternalLink, GraduationCap, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  DOCUMENT_TYPE_LABELS,
  fetchStaffParticipantsCsv,
  formatAge,
  formatDate,
  genderLabel,
  initialsFromName,
  type RegistryApplication,
  type RegistryFilters,
  type RegistryParticipant,
  type RegistryParticipantDetail,
  type RegistryPerformance,
  SUBMISSION_STATUS_LABELS,
  useStaffParticipant,
  useStaffParticipants,
} from "@/features/staff-participants";
import { toApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import { useMediaQuery } from "@/shared/hooks";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Checkbox,
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  EmptyState,
  Input,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Select,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  toast,
} from "@/shared/ui";

type QuickFilterKey = "all" | "solo" | "collective";

const EMPTY_FILTERS: RegistryFilters = { q: "", competitionId: "", participantType: "" };

function statusLabel(status: string): string {
  return SUBMISSION_STATUS_LABELS[status] ?? status;
}

function typeLabel(participantType: RegistryParticipant["participantType"]): string {
  return participantType === "collective" ? "Коллектив" : "Соло";
}

function statusTone(status: string): "success" | "warning" | "neutral" {
  if (status === "COMPLETED") return "success";
  if (status === "SCHEDULED") return "warning";
  return "neutral";
}

/**
 * The processing page filters by a queue derived from status; pointing it at the
 * right queue lets the deep-linked submission be preselected in one click.
 */
function queueForStatus(status: string): string {
  return status === "SCHEDULED" || status === "COMPLETED" ? "RUNNING" : "READY";
}

function applicationHref(application: RegistryApplication): string {
  const params = new URLSearchParams({
    selected: application.submissionId,
    competitionId: application.competitionId,
    queue: queueForStatus(application.status),
  });
  return `${ROUTES.staffApplications}?${params.toString()}`;
}

/** Trigger a client-side download of CSV text as a file. */
function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function StaffParticipantsPage(): React.JSX.Element {
  const [filters, setFilters] = useState<RegistryFilters>(EMPTY_FILTERS);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  // The detail is inline on desktop and a drawer below it; auto-select only on
  // desktop so the drawer never pops open unprompted on small screens.
  const isDesktop = useMediaQuery("(min-width: 1280px)");

  const listQuery = useStaffParticipants(filters);
  const detailQuery = useStaffParticipant(selectedKey);

  const rows = useMemo(() => listQuery.data?.rows ?? [], [listQuery.data]);
  const facets = listQuery.data?.facets;
  const competitions = listQuery.data?.competitions ?? [];
  const total = listQuery.data?.total ?? 0;

  // Keep a live selection: default to the first row on desktop so the detail
  // panel is never empty, and follow the list when filtering drops the current one.
  useEffect(() => {
    if (!isDesktop) return;
    if (rows.length === 0) {
      setSelectedKey(null);
      return;
    }
    if (selectedKey == null || !rows.some((row) => row.key === selectedKey)) {
      setSelectedKey(rows[0]?.key ?? null);
    }
  }, [rows, selectedKey, isDesktop]);

  const activeQuickFilter: QuickFilterKey =
    filters.participantType === "solo"
      ? "solo"
      : filters.participantType === "collective"
        ? "collective"
        : "all";

  const quickFilters: Array<{ key: QuickFilterKey; label: string; count: number | undefined }> = [
    { key: "all", label: "Все", count: facets?.total },
    { key: "solo", label: "Солисты", count: facets?.solo },
    { key: "collective", label: "Коллективы", count: facets?.collective },
  ];

  function applyQuickFilter(key: QuickFilterKey): void {
    setFilters((prev) => ({ ...prev, participantType: key === "all" ? "" : key }));
  }

  function toggleChecked(key: string): void {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll(): void {
    setChecked((prev) =>
      prev.size === rows.length ? new Set() : new Set(rows.map((row) => row.key)),
    );
  }

  async function exportAll(): Promise<void> {
    setExporting(true);
    try {
      downloadCsv("participants.csv", await fetchStaffParticipantsCsv(filters));
    } catch (error) {
      toast.error((await toApiError(error)).message);
    } finally {
      setExporting(false);
    }
  }

  function exportSelected(): void {
    const chosen = rows.filter((row) => checked.has(row.key));
    if (chosen.length === 0) return;
    const header = ["ФИО", "Тип", "Дата рождения", "Возраст", "Пол", "Организация", "Педагоги"];
    const lines = chosen.map((row) =>
      [
        row.fullName,
        typeLabel(row.participantType),
        row.birthDate ?? "",
        row.age ?? "",
        row.gender ? genderLabel(row.gender) : "",
        row.primaryOrganization?.name ?? "",
        row.teachers.map((teacher) => teacher.name).join("; "),
      ]
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(","),
    );
    downloadCsv("participants-selected.csv", [header.join(","), ...lines].join("\n"));
  }

  const detail = detailQuery.data ?? null;
  const allChecked = rows.length > 0 && checked.size === rows.length;
  const filtersActive =
    activeQuickFilter !== "all" || Boolean(filters.q) || Boolean(filters.competitionId);

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Участники</PageTitle>
        <PageDescription>
          Реестр формируется автоматически из подтверждённых заявок фестивалей организации — без
          ручного создания и редактирования.
        </PageDescription>
      </PageHeader>

      <PageContent>
        {/* Toolbar: search + competition + type chips + export — one compact block. */}
        <Card>
          <CardContent className="flex flex-col gap-2 p-3 lg:flex-row lg:items-center">
            <Input
              value={filters.q ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
              placeholder="Поиск: ФИО, организация, педагог"
              leadingIcon={<Search aria-hidden="true" />}
              className="lg:max-w-xs"
            />
            <Select
              placeholder="Все фестивали"
              value={filters.competitionId ?? ""}
              onValueChange={(value) => setFilters((prev) => ({ ...prev, competitionId: value }))}
              options={competitions.map((item) => ({ value: item.id, label: item.title }))}
              size="sm"
              className="lg:w-56"
            />
            <div className="flex flex-wrap items-center gap-1.5">
              {quickFilters.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => applyQuickFilter(item.key)}
                  className={`flex cursor-pointer items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm transition ${
                    activeQuickFilter === item.key
                      ? "border-primary bg-primary/10 text-primary"
                      : "hover:border-primary/50"
                  }`}
                >
                  {item.label}
                  {item.count != null ? (
                    <span className="text-muted-foreground text-xs">{item.count}</span>
                  ) : null}
                </button>
              ))}
              {filtersActive ? (
                <Button variant="ghost" size="sm" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Сбросить
                </Button>
              ) : null}
            </div>
            <div className="flex items-center gap-2 lg:ml-auto">
              {checked.size > 0 ? (
                <Button size="sm" variant="secondary" onClick={exportSelected}>
                  Экспорт выбранных ({checked.size})
                </Button>
              ) : null}
              <Button
                size="sm"
                variant="outline"
                loading={exporting}
                disabled={rows.length === 0}
                onClick={() => void exportAll()}
              >
                Экспорт CSV
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(380px,420px)_1fr]">
          {/* Registry list */}
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-border border-b px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <Checkbox
                  aria-label="Выбрать всех"
                  checked={allChecked}
                  onCheckedChange={() => toggleAll()}
                  disabled={rows.length === 0}
                />
                <span className="font-medium">Найдено участников: {total}</span>
              </div>
            </div>
            <div className="max-h-[calc(100vh-15rem)] divide-y divide-border overflow-auto">
              {listQuery.isLoading ? (
                <div className="space-y-2 p-3">
                  <Skeleton className="h-14" />
                  <Skeleton className="h-14" />
                  <Skeleton className="h-14" />
                </div>
              ) : listQuery.isError ? (
                <EmptyState
                  title="Не удалось загрузить реестр"
                  description={listQuery.error.message}
                  action={
                    <Button variant="outline" onClick={() => listQuery.refetch()}>
                      Повторить
                    </Button>
                  }
                />
              ) : rows.length === 0 ? (
                <EmptyState
                  title={filtersActive ? "Ничего не найдено" : "Пока нет участников"}
                  description={
                    filtersActive
                      ? "Измените условия поиска или сбросьте фильтры."
                      : "Участники появятся автоматически после подтверждения первых заявок."
                  }
                />
              ) : (
                rows.map((row) => (
                  <ParticipantRow
                    key={row.key}
                    row={row}
                    selected={selectedKey === row.key}
                    checked={checked.has(row.key)}
                    onSelect={() => setSelectedKey(row.key)}
                    onToggle={() => toggleChecked(row.key)}
                  />
                ))
              )}
            </div>
          </Card>

          {/* Desktop detail */}
          <Card className="hidden xl:block">
            <ParticipantDetail
              detail={detail}
              loading={detailQuery.isLoading}
              selected={selectedKey != null}
            />
          </Card>
        </div>
      </PageContent>

      {/* Mobile detail drawer */}
      <Drawer
        open={selectedKey != null && !isDesktop}
        onOpenChange={(open) => {
          if (!open) setSelectedKey(null);
        }}
      >
        <DrawerContent side="right" className="w-full max-w-2xl">
          <DrawerHeader>
            <DrawerTitle>{detail?.fullName ?? "Карточка участника"}</DrawerTitle>
          </DrawerHeader>
          <div className="overflow-y-auto px-4 pb-6">
            <ParticipantDetail detail={detail} loading={detailQuery.isLoading} selected hideName />
          </div>
        </DrawerContent>
      </Drawer>
    </PageContainer>
  );
}

function ParticipantRow({
  row,
  selected,
  checked,
  onSelect,
  onToggle,
}: {
  row: RegistryParticipant;
  selected: boolean;
  checked: boolean;
  onSelect: () => void;
  onToggle: () => void;
}): React.JSX.Element {
  const teacher = row.teachers[0]?.name;
  return (
    <div
      className={`flex items-start gap-2 px-3 py-2 transition ${
        selected ? "bg-primary/10" : "hover:bg-muted/50"
      }`}
    >
      <Checkbox
        aria-label={`Выбрать ${row.fullName}`}
        checked={checked}
        onCheckedChange={() => onToggle()}
        className="mt-1"
      />
      <button
        type="button"
        onClick={onSelect}
        className="flex min-w-0 flex-1 cursor-pointer items-start gap-2.5 text-left"
      >
        <Avatar size="sm" fallback={initialsFromName(row.fullName)} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-medium text-sm">{row.fullName}</p>
            <span className="shrink-0 text-muted-foreground text-xs">
              {formatDate(row.lastActivity)}
            </span>
          </div>
          <p className="truncate text-muted-foreground text-xs">
            {row.participantType === "collective"
              ? `Коллектив · ${row.memberCount} чел.`
              : `${formatAge(row.age)}${row.gender ? ` · ${genderLabel(row.gender)}` : ""}`}
            {row.primaryOrganization ? ` · ${row.primaryOrganization.name}` : ""}
          </p>
          <div className="mt-0.5 flex items-center gap-2 text-muted-foreground text-xs">
            {teacher ? (
              <span className="flex min-w-0 items-center gap-1">
                <GraduationCap className="size-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{teacher}</span>
              </span>
            ) : null}
            <span className="ml-auto shrink-0">
              Фестивалей: {row.competitionsCount} · Заявок: {row.applicationsCount}
            </span>
          </div>
        </div>
      </button>
    </div>
  );
}

function ParticipantDetail({
  detail,
  loading,
  selected,
  hideName = false,
}: {
  detail: RegistryParticipantDetail | null;
  loading: boolean;
  selected: boolean;
  hideName?: boolean;
}): React.JSX.Element {
  if (!selected) {
    return (
      <CardContent className="flex min-h-[40vh] items-center justify-center">
        <p className="text-muted-foreground text-sm">
          Выберите участника из реестра, чтобы открыть карточку.
        </p>
      </CardContent>
    );
  }
  if (loading || detail == null) {
    return (
      <CardContent className="space-y-3 pt-6">
        <Skeleton className="h-14" />
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </CardContent>
    );
  }

  const teacher = detail.teachers[0]?.name;
  const metrics: Array<{ label: string; value: string }> = [
    { label: "Фестивалей", value: String(detail.competitionsCount) },
    { label: "Заявок", value: String(detail.applicationsCount) },
    { label: "Выступлений", value: String(detail.performancesCount) },
    { label: "Наград", value: String(detail.awards.length) },
    { label: "Документов", value: String(detail.documentsCount) },
    { label: "Последнее участие", value: formatDate(detail.lastActivity) },
  ];

  return (
    <>
      {hideName ? null : (
        <CardHeader className="flex-row items-center gap-3 space-y-0 border-border border-b pb-4">
          <Avatar size="lg" fallback={initialsFromName(detail.fullName)} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-semibold text-lg">{detail.fullName}</h2>
              <Badge variant="secondary">{typeLabel(detail.participantType)}</Badge>
            </div>
            <p className="text-muted-foreground text-sm">
              {detail.participantType === "collective"
                ? `Коллектив · ${detail.memberCount} чел.`
                : `${formatAge(detail.age)} · ${genderLabel(detail.gender)} · ${formatDate(detail.birthDate)}`}
              {detail.primaryOrganization ? ` · ${detail.primaryOrganization.name}` : ""}
              {teacher ? ` · педагог: ${teacher}` : ""}
            </p>
          </div>
        </CardHeader>
      )}
      <CardContent className="space-y-4 pt-4">
        {/* Summary metric strip */}
        <div className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-6">
          {metrics.map((metric) => (
            <div key={metric.label} className="bg-card px-2 py-2 text-center">
              <div className="truncate font-semibold text-base" title={metric.value}>
                {metric.value}
              </div>
              <div className="text-[11px] text-muted-foreground leading-tight">{metric.label}</div>
            </div>
          ))}
        </div>

        {/* Always-visible essentials */}
        <div className="grid gap-3 md:grid-cols-2">
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-sm">
            {detail.participantType === "collective" ? (
              <>
                <Fact label="Название" value={detail.displayName} />
                <Fact label="Тип" value="Коллектив" />
                <Fact label="Участников" value={String(detail.memberCount)} />
              </>
            ) : (
              <>
                <Fact label="Фамилия" value={detail.lastName} />
                <Fact label="Имя" value={detail.firstName} />
                <Fact label="Отчество" value={detail.middleName} />
                <Fact label="Дата рождения" value={formatDate(detail.birthDate)} />
                <Fact label="Возраст" value={formatAge(detail.age)} />
                <Fact label="Пол" value={genderLabel(detail.gender)} />
              </>
            )}
          </dl>
          <div className="space-y-2">
            <MiniSection icon={<Building2 className="size-3.5" />} title="Организации">
              {detail.organizations.length === 0 ? (
                <span className="text-muted-foreground text-sm">Не указаны</span>
              ) : (
                detail.organizations.map((org) => (
                  <Badge
                    key={org.id ?? org.name}
                    variant={
                      detail.primaryOrganization?.name === org.name ? "primary" : "secondary"
                    }
                  >
                    {org.name}
                  </Badge>
                ))
              )}
            </MiniSection>
            <MiniSection icon={<GraduationCap className="size-3.5" />} title="Педагоги">
              {detail.teachers.length === 0 ? (
                <span className="text-muted-foreground text-sm">Не указаны</span>
              ) : (
                detail.teachers.map((item) => (
                  <Badge key={`${item.name}-${item.role}`} variant="outline">
                    {item.name}
                  </Badge>
                ))
              )}
            </MiniSection>
          </div>
        </div>

        <Tabs defaultValue="history" className="space-y-3">
          <TabsList className="w-full justify-start overflow-x-auto">
            <TabsTrigger value="history">
              История участия ({detail.applications.length})
            </TabsTrigger>
            <TabsTrigger value="documents">Документы ({detail.documents.length})</TabsTrigger>
            <TabsTrigger value="notes">Заметки ({detail.notes.length})</TabsTrigger>
            <TabsTrigger value="awards">Награды ({detail.awards.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="history" className="space-y-2">
            {detail.applications.length === 0 ? (
              <p className="py-6 text-center text-muted-foreground text-sm">
                Участие в фестивалях организации пока отсутствует.
              </p>
            ) : (
              detail.applications.map((application) => (
                <ParticipationRow
                  key={application.submissionId}
                  application={application}
                  performance={detail.performances.find(
                    (item) => item.submissionId === application.submissionId,
                  )}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="documents" className="space-y-1.5">
            {detail.documents.length === 0 ? (
              <p className="py-6 text-center text-muted-foreground text-sm">
                Документы, загруженные в заявках, появятся здесь.
              </p>
            ) : (
              detail.documents.map((document) => (
                <div
                  key={document.id}
                  className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {document.caption || DOCUMENT_TYPE_LABELS[document.type] || document.type}
                    </p>
                    <p className="truncate text-muted-foreground text-xs">
                      {DOCUMENT_TYPE_LABELS[document.type] ?? document.type} ·{" "}
                      {document.competition}
                    </p>
                  </div>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="notes" className="space-y-1.5">
            {detail.notes.length === 0 ? (
              <p className="py-6 text-center text-muted-foreground text-sm">
                Внутренних заметок организаторов пока нет.
              </p>
            ) : (
              detail.notes.map((note) => (
                <div
                  key={`${note.submissionId}-${note.createdAt ?? ""}-${note.text.length}`}
                  className="rounded-md border px-3 py-2"
                >
                  <p className="text-sm">{note.text}</p>
                  <p className="mt-0.5 text-muted-foreground text-xs">
                    {note.competition} · {formatDate(note.createdAt)}
                  </p>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="awards">
            <p className="py-6 text-center text-muted-foreground text-sm">
              Награды появятся автоматически, когда заработает модуль результатов и судейства.
            </p>
          </TabsContent>
        </Tabs>
      </CardContent>
    </>
  );
}

function ParticipationRow({
  application,
  performance,
}: {
  application: RegistryApplication;
  performance: RegistryPerformance | undefined;
}): React.JSX.Element {
  const navigate = useNavigate();
  const tags = [
    performance?.nomination,
    performance?.discipline,
    performance?.ageCategory,
    performance?.participationFormat,
  ].filter((value): value is string => Boolean(value));

  return (
    <div className="rounded-md border p-2.5 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{application.competition}</span>
            <Badge variant={statusTone(application.status)}>
              {statusLabel(application.status)}
            </Badge>
          </div>
          <p className="truncate text-muted-foreground text-xs">
            {performance?.title || application.performanceTitle || "Номер без названия"}
            {" · "}
            {formatDate(application.submittedAt)}
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="shrink-0"
          onClick={() => navigate(applicationHref(application))}
          rightIcon={<ExternalLink className="size-3.5" aria-hidden="true" />}
        >
          Открыть заявку
        </Button>
      </div>
      {tags.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {tags.map((tag) => (
            <Badge key={`${application.submissionId}-${tag}`} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      ) : null}
      {application.teachers.length > 0 ? (
        <p className="mt-1 truncate text-muted-foreground text-xs">
          Педагоги: {application.teachers.map((item) => item.name).join(", ")}
        </p>
      ) : null}
      {performance?.comment?.trim() ? (
        <div className="mt-1.5">
          <p className="font-medium text-xs">Дополнительная информация</p>
          <p className="whitespace-pre-line text-muted-foreground text-xs">
            {performance.comment.trim()}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string | null }): React.JSX.Element {
  return (
    <div className="contents">
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-right font-medium text-sm">{value && value.length > 0 ? value : "—"}</dd>
    </div>
  );
}

function MiniSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5 font-medium text-muted-foreground text-xs">
        {icon}
        {title}
      </div>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}
