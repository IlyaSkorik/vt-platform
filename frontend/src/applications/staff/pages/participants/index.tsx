import {
  Award,
  Building2,
  Calendar,
  Download,
  FileText,
  GraduationCap,
  Search,
  StickyNote,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  DOCUMENT_TYPE_LABELS,
  fetchStaffParticipantsCsv,
  formatAge,
  formatDate,
  GENDER_LABELS,
  initialsFromName,
  type RegistryFilters,
  type RegistryParticipant,
  type RegistryParticipantDetail,
  SUBMISSION_STATUS_LABELS,
  useStaffParticipant,
  useStaffParticipants,
} from "@/features/staff-participants";
import { toApiError } from "@/shared/api";
import { useMediaQuery } from "@/shared/hooks";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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

type QuickFilterKey = "all" | "solo" | "collective" | "withDocuments" | "female" | "male";

const EMPTY_FILTERS: RegistryFilters = {
  q: "",
  gender: "",
  ageMin: "",
  ageMax: "",
  competitionId: "",
  organization: "",
  participantType: "",
  hasDocuments: false,
};

function statusLabel(status: string): string {
  return SUBMISSION_STATUS_LABELS[status] ?? status;
}

function typeLabel(participantType: RegistryParticipant["participantType"]): string {
  return participantType === "collective" ? "Коллектив" : "Соло";
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
  // The detail lives inline on desktop; the drawer is only for narrow screens,
  // so it must never open (and never render its backdrop) at xl and up.
  const isDesktop = useMediaQuery("(min-width: 1280px)");

  const listQuery = useStaffParticipants(filters);
  const detailQuery = useStaffParticipant(selectedKey);

  const rows = useMemo(() => listQuery.data?.rows ?? [], [listQuery.data]);
  const facets = listQuery.data?.facets;
  const competitions = listQuery.data?.competitions ?? [];
  const total = listQuery.data?.total ?? 0;

  const activeQuickFilter: QuickFilterKey = filters.hasDocuments
    ? "withDocuments"
    : filters.participantType === "solo"
      ? "solo"
      : filters.participantType === "collective"
        ? "collective"
        : filters.gender === "female"
          ? "female"
          : filters.gender === "male"
            ? "male"
            : "all";

  const quickFilters: Array<{ key: QuickFilterKey; label: string; count: number | undefined }> = [
    { key: "all", label: "Все", count: facets?.total },
    { key: "solo", label: "Соло", count: facets?.solo },
    { key: "collective", label: "Коллективы", count: facets?.collective },
    { key: "withDocuments", label: "С документами", count: facets?.withDocuments },
    { key: "female", label: "Девочки", count: facets?.female },
    { key: "male", label: "Мальчики", count: facets?.male },
  ];

  function applyQuickFilter(key: QuickFilterKey): void {
    setFilters((prev) => ({
      ...prev,
      participantType: key === "solo" ? "solo" : key === "collective" ? "collective" : "",
      gender: key === "female" ? "female" : key === "male" ? "male" : "",
      hasDocuments: key === "withDocuments",
    }));
  }

  function toggleChecked(key: string): void {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
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
      const csv = await fetchStaffParticipantsCsv(filters);
      downloadCsv("participants.csv", csv);
    } catch (error) {
      toast.error((await toApiError(error)).message);
    } finally {
      setExporting(false);
    }
  }

  function exportSelected(): void {
    const chosen = rows.filter((row) => checked.has(row.key));
    if (chosen.length === 0) {
      return;
    }
    const header = ["ФИО", "Тип", "Дата рождения", "Возраст", "Пол", "Организация", "Педагоги"];
    const lines = chosen.map((row) =>
      [
        row.fullName,
        typeLabel(row.participantType),
        row.birthDate ?? "",
        row.age ?? "",
        row.gender ? GENDER_LABELS[row.gender] : "",
        row.primaryOrganization?.name ?? "",
        row.teachers.map((teacher) => teacher.name).join("; "),
      ]
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(","),
    );
    downloadCsv("participants-selected.csv", [header.join(","), ...lines].join("\n"));
  }

  const detail = detailQuery.data ?? null;
  const noFiltersActive =
    !filters.q &&
    activeQuickFilter === "all" &&
    !filters.competitionId &&
    !filters.ageMin &&
    !filters.ageMax;

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Участники</PageTitle>
        <PageDescription>
          Реестр формируется автоматически из подтверждённых заявок конкурсов вашей организации.
          Записи не создаются и не редактируются вручную.
        </PageDescription>
      </PageHeader>

      <PageContent>
        <div className="space-y-3">
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap items-center gap-2">
                {quickFilters.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => applyQuickFilter(item.key)}
                    className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition ${
                      activeQuickFilter === item.key
                        ? "border-primary bg-primary/10 text-primary"
                        : "hover:border-primary/50"
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.count != null ? <Badge>{item.count}</Badge> : null}
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-2">
                  {checked.size > 0 ? (
                    <Button size="sm" variant="secondary" onClick={exportSelected}>
                      <Download aria-hidden="true" /> Экспорт выбранных ({checked.size})
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    variant="outline"
                    loading={exporting}
                    disabled={rows.length === 0}
                    onClick={() => void exportAll()}
                  >
                    <Download aria-hidden="true" /> Экспорт CSV
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="grid gap-2 pt-4 md:grid-cols-2 xl:grid-cols-4">
              <Input
                value={filters.q ?? ""}
                onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
                placeholder="Поиск: ФИО, организация, педагог"
                leadingIcon={<Search aria-hidden="true" />}
              />
              <Select
                placeholder="Все конкурсы"
                value={filters.competitionId ?? ""}
                onValueChange={(value) => setFilters((prev) => ({ ...prev, competitionId: value }))}
                options={competitions.map((item) => ({ value: item.id, label: item.title }))}
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  min={0}
                  value={filters.ageMin ?? ""}
                  onChange={(event) =>
                    setFilters((prev) => ({ ...prev, ageMin: event.target.value }))
                  }
                  placeholder="Возраст от"
                />
                <Input
                  type="number"
                  min={0}
                  value={filters.ageMax ?? ""}
                  onChange={(event) =>
                    setFilters((prev) => ({ ...prev, ageMax: event.target.value }))
                  }
                  placeholder="до"
                />
              </div>
              <Button variant="ghost" onClick={() => setFilters(EMPTY_FILTERS)}>
                Сбросить фильтры
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="mt-3 grid gap-4 xl:grid-cols-[minmax(340px,380px)_1fr]">
          <Card>
            <CardHeader className="gap-1">
              <div className="flex items-center justify-between">
                <CardTitle>Реестр</CardTitle>
                {rows.length > 0 ? (
                  <Checkbox
                    aria-label="Выбрать всех"
                    checked={checked.size === rows.length && rows.length > 0}
                    onCheckedChange={() => toggleAll()}
                  />
                ) : null}
              </div>
              <CardDescription>Найдено участников: {total}</CardDescription>
            </CardHeader>
            <CardContent className="max-h-[65vh] space-y-2 overflow-auto [scrollbar-color:var(--border-default)_transparent] [scrollbar-width:thin]">
              {listQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-16" />
                  <Skeleton className="h-16" />
                  <Skeleton className="h-16" />
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
                  title={noFiltersActive ? "Пока нет участников" : "Ничего не найдено"}
                  description={
                    noFiltersActive
                      ? "Участники появятся автоматически после подтверждения первых заявок."
                      : "Измените условия поиска или сбросьте фильтры."
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
            </CardContent>
          </Card>

          {/* Desktop detail pane */}
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
          if (!open) {
            setSelectedKey(null);
          }
        }}
      >
        <DrawerContent side="right" className="w-full max-w-xl">
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
  return (
    <div
      className={`flex items-start gap-2 rounded-md border p-2.5 transition ${
        selected ? "border-primary bg-primary/5" : "hover:border-primary/50"
      }`}
    >
      <Checkbox
        aria-label={`Выбрать ${row.fullName}`}
        checked={checked}
        onCheckedChange={() => onToggle()}
      />
      <button
        type="button"
        onClick={onSelect}
        className="flex flex-1 cursor-pointer items-start gap-3 text-left"
      >
        <Avatar size="sm" fallback={initialsFromName(row.fullName)} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{row.fullName}</p>
          <p className="truncate text-muted-foreground text-xs">
            {row.participantType === "collective"
              ? `Коллектив · ${row.memberCount} чел.`
              : `${formatAge(row.age)}${row.gender ? ` · ${GENDER_LABELS[row.gender]}` : ""}`}
          </p>
          <p className="truncate text-muted-foreground text-xs">
            {row.primaryOrganization?.name ?? "Организация не указана"}
          </p>
          <div className="mt-1 flex flex-wrap gap-1">
            <Badge variant="secondary">Заявок: {row.applicationsCount}</Badge>
            {row.performancesCount > 0 ? (
              <Badge variant="outline">Номеров: {row.performancesCount}</Badge>
            ) : null}
            {row.documentsCount > 0 ? (
              <Badge variant="outline">Док.: {row.documentsCount}</Badge>
            ) : null}
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
        <Skeleton className="h-12" />
        <Skeleton className="h-40" />
      </CardContent>
    );
  }

  return (
    <>
      {hideName ? null : (
        <CardHeader className="flex-row items-start gap-4 space-y-0">
          <Avatar size="lg" fallback={initialsFromName(detail.fullName)} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{detail.fullName}</CardTitle>
              <Badge>{typeLabel(detail.participantType)}</Badge>
            </div>
            <CardDescription>
              {detail.participantType === "collective"
                ? `Участников в коллективе: ${detail.memberCount}`
                : `${formatAge(detail.age)} · ${detail.gender ? GENDER_LABELS[detail.gender] : "—"} · ${formatDate(detail.birthDate)}`}
            </CardDescription>
          </div>
        </CardHeader>
      )}
      <CardContent>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="w-full justify-start overflow-x-auto">
            <TabsTrigger value="overview">Обзор</TabsTrigger>
            <TabsTrigger value="applications">Заявки ({detail.applications.length})</TabsTrigger>
            <TabsTrigger value="performances">
              Выступления ({detail.performances.length})
            </TabsTrigger>
            <TabsTrigger value="awards">Награды</TabsTrigger>
            <TabsTrigger value="history">История ({detail.history.length})</TabsTrigger>
            <TabsTrigger value="documents">Документы ({detail.documents.length})</TabsTrigger>
            <TabsTrigger value="notes">Заметки ({detail.notes.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Fact label="Фамилия" value={detail.lastName} />
              <Fact label="Имя" value={detail.firstName} />
              <Fact label="Отчество" value={detail.middleName} />
              <Fact label="Дата рождения" value={formatDate(detail.birthDate)} />
              <Fact label="Возраст" value={formatAge(detail.age)} />
              <Fact label="Пол" value={detail.gender ? GENDER_LABELS[detail.gender] : "—"} />
              <Fact label="Конкурсов" value={String(detail.competitionsCount)} />
              <Fact label="Заявок" value={String(detail.applicationsCount)} />
            </dl>
            <Section icon={<Building2 className="size-4" />} title="Организации">
              {detail.organizations.length === 0 ? (
                <p className="text-muted-foreground text-sm">Не указаны</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {detail.organizations.map((org) => (
                    <Badge
                      key={org.id ?? org.name}
                      variant={
                        detail.primaryOrganization?.name === org.name ? "primary" : "secondary"
                      }
                    >
                      {org.name}
                    </Badge>
                  ))}
                </div>
              )}
            </Section>
            <Section icon={<GraduationCap className="size-4" />} title="Педагоги">
              {detail.teachers.length === 0 ? (
                <p className="text-muted-foreground text-sm">Не указаны</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {detail.teachers.map((teacher) => (
                    <Badge key={`${teacher.name}-${teacher.role}`} variant="outline">
                      {teacher.name}
                    </Badge>
                  ))}
                </div>
              )}
            </Section>
          </TabsContent>

          <TabsContent value="applications" className="space-y-2">
            {detail.applications.length === 0 ? (
              <EmptyState
                title="Заявок нет"
                description="Участник ещё не участвовал в конкурсах организации."
              />
            ) : (
              detail.applications.map((application) => (
                <div key={application.submissionId} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium">{application.competition}</p>
                    <Badge>{statusLabel(application.status)}</Badge>
                  </div>
                  {application.performanceTitle ? (
                    <p className="text-muted-foreground text-sm">{application.performanceTitle}</p>
                  ) : null}
                  <p className="text-muted-foreground text-xs">
                    {application.organization ?? "Организация не указана"} · Подана{" "}
                    {formatDate(application.submittedAt)}
                  </p>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="performances" className="space-y-2">
            {detail.performances.length === 0 ? (
              <EmptyState
                title="Выступлений нет"
                description="Данные о номерах появятся из подтверждённых заявок."
              />
            ) : (
              detail.performances.map((performance) => (
                <div key={performance.submissionId} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium">{performance.title || "Без названия"}</p>
                    <Badge variant="outline">{performance.competition}</Badge>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1 text-muted-foreground text-xs">
                    {[
                      performance.nomination,
                      performance.discipline,
                      performance.ageCategory,
                      performance.participationFormat,
                    ]
                      .filter((value): value is string => Boolean(value))
                      .map((value) => (
                        <Badge key={`${performance.submissionId}-${value}`} variant="secondary">
                          {value}
                        </Badge>
                      ))}
                  </div>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="awards">
            <EmptyState
              icon={<Award className="size-6" aria-hidden="true" />}
              title="Наград пока нет"
              description="Раздел готов к подключению: награды появятся автоматически, когда заработает модуль результатов и судейства."
            />
          </TabsContent>

          <TabsContent value="history" className="space-y-2">
            {detail.history.length === 0 ? (
              <EmptyState
                title="История пуста"
                description="Здесь появится участие в конкурсах организации."
              />
            ) : (
              detail.history.map((entry) => (
                <div
                  key={`${entry.submissionId}-${entry.date}`}
                  className="flex items-center justify-between gap-2 rounded-md border p-3"
                >
                  <div className="flex items-center gap-2">
                    <Calendar className="size-4 text-muted-foreground" aria-hidden="true" />
                    <div>
                      <p className="font-medium">{entry.competition}</p>
                      <p className="text-muted-foreground text-xs">{formatDate(entry.date)}</p>
                    </div>
                  </div>
                  <Badge>{statusLabel(entry.status)}</Badge>
                </div>
              ))
            )}
          </TabsContent>

          <TabsContent value="documents" className="space-y-2">
            {detail.documents.length === 0 ? (
              <EmptyState
                title="Документов нет"
                description="Файлы, загруженные в заявках, появятся здесь."
              />
            ) : (
              detail.documents.map((document) => (
                <div key={document.id} className="flex items-center gap-2 rounded-md border p-3">
                  <FileText className="size-4 text-muted-foreground" aria-hidden="true" />
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

          <TabsContent value="notes" className="space-y-2">
            {detail.notes.length === 0 ? (
              <EmptyState
                icon={<StickyNote className="size-6" aria-hidden="true" />}
                title="Заметок нет"
                description="Внутренние заметки организаторов из заявок появятся здесь."
              />
            ) : (
              detail.notes.map((note) => (
                <div
                  key={`${note.submissionId}-${note.createdAt ?? ""}-${note.text.length}`}
                  className="rounded-md border p-3"
                >
                  <p className="text-sm">{note.text}</p>
                  <p className="mt-1 text-muted-foreground text-xs">
                    {note.competition} · {formatDate(note.createdAt)}
                  </p>
                </div>
              ))
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </>
  );
}

function Fact({ label, value }: { label: string; value: string | null }): React.JSX.Element {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="font-medium">{value && value.length > 0 ? value : "—"}</dd>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 font-medium text-sm">
        {icon}
        {title}
      </div>
      {children}
    </div>
  );
}
