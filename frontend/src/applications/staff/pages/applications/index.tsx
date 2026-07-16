import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/shared/api";
import { resolveMediaUrl } from "@/features/competitions/lib/media-url";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  LoadingState,
  Select,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Textarea,
} from "@/shared/ui";

type Capability = { key: string; label: string };
type Queue = { key: string; label: string; count: number };
type Item = {
  id: string;
  applicationId?: string | null;
  applicationNumber: string;
  competition: string;
  applicant: string;
  performancesCount: number;
  participantsCount: number;
  status: string;
  queue: string;
  paymentStatus: string;
  hasReceipt?: boolean;
  receiptFileReference?: string | null;
  capabilities: Capability[];
};
type Detail = {
  id: string;
  status: string;
  performance: string | null;
  performances?: Array<{
    submissionId: string;
    title: string;
    status: string;
    nominationName?: string | null;
    disciplineName?: string | null;
    ageCategoryName?: string | null;
    participantGroupName?: string | null;
    participationFormatName?: string | null;
    durationSeconds?: number | null;
    participantsCount?: number | null;
    teachersCount?: number | null;
    participants?: Array<{ id: string; name: string; memberCount: number }>;
    teachers?: Array<{ id: string; name: string; role: string }>;
    priceAmount?: string | null;
    priceCurrency?: string | null;
    attachments?: Array<{ id: string; type: string; fileReference: string }>;
  }>;
  price?: string | null;
  totalPriceAmount?: string | null;
  totalPriceCurrency?: string | null;
  receiptFileReference?: string | null;
  participants: Array<{ id: string; name: string; memberCount: number }>;
  teachers: Array<{ id: string; name: string; role: string }>;
  attachments: Array<{ id: string; type: string; fileReference: string }>;
  timeline: Array<{ kind: string; label: string; at: string }>;
  audit: Array<{ at: string; by: string; reason: string }>;
  internalNotes?: Array<{ text: string; created_at: string }>;
  participantMessages?: Array<{ text: string; created_at: string }>;
};
type Workspace = {
  queues: Queue[];
  applications: Item[];
  selected: string | null;
  detail: Detail | null;
  metrics: Record<string, number>;
};

async function fetchWorkspace(
  queue: string,
  q: string,
  filters: Record<string, string>,
): Promise<Workspace> {
  const search = new URLSearchParams();
  if (queue) search.set("queue", queue);
  if (q) search.set("q", q);
  for (const [key, value] of Object.entries(filters)) {
    if (value) search.set(key, value);
  }
  const response = await apiClient.get(`staff/applications/workspace?${search.toString()}`);
  const body = (await response.json()) as { data: Workspace };
  return body.data;
}

async function runAction(submissionId: string, action: string, comment: string): Promise<void> {
  await apiClient.post(`staff/applications/${submissionId}/actions/${action}`, { json: { comment } });
}

function primaryAction(capabilities: Capability[]): Capability | null {
  const preferred = capabilities.find((item) => item.key !== "cancel");
  return preferred ?? capabilities[0] ?? null;
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    DRAFT: "Черновик",
    SUBMITTED: "Подана",
    UNDER_REVIEW: "На проверке",
    REQUIRES_CORRECTION: "Требует исправлений",
    APPROVED: "Одобрена",
    WAITING_PAYMENT: "Ожидает оплаты",
    PAID: "Оплачена",
    ACCEPTED: "Подтверждена",
    SCHEDULED: "В конкурсе",
    COMPLETED: "Завершена",
    CANCELLED: "Отменена",
  };
  return map[status] ?? status;
}

function paymentStatusLabel(status: string): string {
  const map: Record<string, string> = {
    RECEIPT_MISSING: "Квитанция не прикреплена",
    RECEIPT_ATTACHED: "Квитанция прикреплена",
  };
  return map[status] ?? status;
}

function receiptDownloadUrl(reference: string | null | undefined): string | null {
  const value = reference?.trim();
  if (!value) return null;
  if (/^(https?:|blob:|data:)/i.test(value)) return value;
  if (value.startsWith("/media/") || value.startsWith("media/")) return resolveMediaUrl(value);
  const normalized = value.startsWith("/") ? `/media${value}` : `/media/${value}`;
  return resolveMediaUrl(normalized);
}

function attachmentTypeLabel(type: string): string {
  const map: Record<string, string> = {
    MUSIC: "Музыка",
    VIDEO: "Видео",
    DOCUMENT: "Документ",
    RECEIPT: "Квитанция",
    OTHER: "Файл",
  };
  return map[type] ?? type;
}

function nextId(items: Item[], currentId: string | null): string | null {
  const first = items[0];
  if (!items.length) return null;
  if (!first) return null;
  if (!currentId) return first.id;
  const index = items.findIndex((item) => item.id === currentId);
  if (index < 0) return first.id;
  return items[index + 1]?.id ?? items[index - 1]?.id ?? null;
}

function statusPriority(status: string): number {
  const map: Record<string, number> = {
    UNDER_REVIEW: 0,
    SUBMITTED: 1,
    REQUIRES_CORRECTION: 2,
    APPROVED: 3,
    WAITING_PAYMENT: 4,
    PAID: 5,
    ACCEPTED: 6,
    SCHEDULED: 7,
    COMPLETED: 8,
    CANCELLED: 9,
  };
  return map[status] ?? 100;
}

export function StaffApplicationsProcessingPage(): React.JSX.Element {
  const [queue, setQueue] = useState("NEW");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [teacher, setTeacher] = useState("");
  const [organization, setOrganization] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [hasCorrections, setHasCorrections] = useState("");
  const [hasMissingFiles, setHasMissingFiles] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [openPerformances, setOpenPerformances] = useState<Record<string, boolean>>({});
  const queryClient = useQueryClient();

  const workspace = useQuery({
    queryKey: [
      "staff",
      "applications",
      "workspace",
      queue,
      q,
      teacher,
      organization,
      dateFrom,
      dateTo,
      hasCorrections,
      hasMissingFiles,
    ],
    queryFn: () =>
      fetchWorkspace(queue, q, {
        teacher,
        organization,
        from: dateFrom,
        to: dateTo,
        hasCorrections,
        hasMissingFiles,
      }),
  });

  const selectedItem = useMemo(
    () => workspace.data?.applications.find((item) => item.id === selected) ?? null,
    [workspace.data, selected],
  );
  const selectedPrimaryAction = primaryAction(selectedItem?.capabilities ?? []);
  const inbox = workspace.data?.applications ?? [];
  const groupedInbox = useMemo(() => {
    const map = new Map<string, Item>();
    for (const item of inbox) {
      const key = item.applicationId ?? item.id;
      const existing = map.get(key);
      if (!existing) {
        map.set(key, { ...item });
        continue;
      }
      const better = statusPriority(item.status) < statusPriority(existing.status) ? item : existing;
      map.set(key, {
        ...better,
        performancesCount: existing.performancesCount + item.performancesCount,
        participantsCount: existing.participantsCount + item.participantsCount,
      });
    }
    return Array.from(map.values());
  }, [inbox]);

  const action = useMutation({
    mutationFn: ({ submissionId, actionKey }: { submissionId: string; actionKey: string }) =>
      runAction(submissionId, actionKey, comment),
    onSuccess: async () => {
      const next = nextId(groupedInbox, selectedItem?.id ?? null);
      setComment("");
      setSelected(next);
      await queryClient.invalidateQueries({ queryKey: ["staff", "applications", "workspace"] });
    },
  });

  useEffect(() => {
    if (!groupedInbox.length) {
      setSelected(null);
      return;
    }
    if (selected && groupedInbox.some((item) => item.id === selected)) {
      return;
    }
    setSelected(groupedInbox[0]?.id ?? null);
  }, [groupedInbox, selected]);

  useEffect(() => {
    setOpenPerformances({});
  }, [selected]);

  if (workspace.isLoading || !workspace.data) {
    return <LoadingState label="Загружаем пространство обработки заявок..." />;
  }

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Обработка заявок</PageTitle>
        <PageDescription>Режим задач: берите следующую заявку, выполняйте действие, переходите дальше.</PageDescription>
      </PageHeader>
      <PageContent>
        <div className="space-y-3">
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-2">
                {workspace.data.queues.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setQueue(item.key)}
                    className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition hover:border-primary/50"
                  >
                    <span>{item.label}</span>
                    <Badge>{item.count}</Badge>
                  </button>
                ))}
                <Button
                  size="sm"
                  variant="outline"
                  className="ml-auto"
                  onClick={() => setSelected(nextId(groupedInbox, selectedItem?.id ?? null))}
                >
                  Следующая заявка
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="mt-3 grid gap-4 xl:grid-cols-[360px_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>Входящие заявки</CardTitle>
              <CardDescription>
                {groupedInbox.length === 0 ? "Очередь пуста" : `Всего заявок в очереди: ${groupedInbox.length}`}
              </CardDescription>
              <Input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Поиск по номеру/конкурсу/заявителю" />
              <Button size="sm" variant="ghost" className="w-fit px-0" onClick={() => setFiltersOpen((value) => !value)}>
                {filtersOpen ? "Скрыть фильтры" : "Показать фильтры"}
              </Button>
              {filtersOpen ? (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <Input value={teacher} onChange={(event) => setTeacher(event.target.value)} placeholder="Фильтр по педагогу" />
                  <Input
                    value={organization}
                    onChange={(event) => setOrganization(event.target.value)}
                    placeholder="Фильтр по организации"
                  />
                  <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                  <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                  <Select
                    placeholder="Есть исправления?"
                    value={hasCorrections}
                    onValueChange={(value) => setHasCorrections(value)}
                    options={[
                      { value: "true", label: "Да" },
                      { value: "false", label: "Нет" },
                    ]}
                  />
                  <Select
                    placeholder="Есть недостающие файлы?"
                    value={hasMissingFiles}
                    onValueChange={(value) => setHasMissingFiles(value)}
                    options={[
                      { value: "true", label: "Да" },
                      { value: "false", label: "Нет" },
                    ]}
                  />
                </div>
              ) : null}
            </CardHeader>
            <CardContent className="max-h-[65vh] space-y-2 overflow-auto">
              {groupedInbox.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelected(item.id)}
                  className="w-full rounded-md border p-3 text-left transition hover:border-primary/50"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium">#{item.applicationNumber}</p>
                    <Badge>{statusLabel(item.status)}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{item.competition}</p>
                  <p className="text-sm text-muted-foreground">
                    {item.applicant} · Номеров: {item.performancesCount} · Участников: {item.participantsCount}
                  </p>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Рабочая карточка</CardTitle>
              <CardDescription>Минимум кликов: одно главное действие и контекст рядом.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!workspace.data.detail || !selectedItem ? (
                <p className="text-sm text-muted-foreground">Выберите заявку из очереди.</p>
              ) : (
                <>
                  <div>
                    <p className="font-medium">{selectedItem.competition}</p>
                    <p className="text-sm text-muted-foreground">
                      {(workspace.data.detail.performances ?? []).length > 0
                        ? `Выступлений в заявке: ${workspace.data.detail.performances?.length ?? 0}`
                        : (workspace.data.detail.performance ?? "Без названия номера")}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Статус: <span className="font-medium text-foreground">{statusLabel(selectedItem.status)}</span>
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Оплата:{" "}
                      <span className="font-medium text-foreground">
                        {paymentStatusLabel(selectedItem.paymentStatus)}
                      </span>
                      {workspace.data.detail.totalPriceAmount
                        ? ` · ${workspace.data.detail.totalPriceAmount} ${workspace.data.detail.totalPriceCurrency ?? "BYN"}`
                        : ""}
                    </p>
                    {receiptDownloadUrl(workspace.data.detail.receiptFileReference ?? selectedItem.receiptFileReference) ? (
                      <div className="mt-2">
                        <Button asChild size="sm" variant="outline">
                          <a
                            href={receiptDownloadUrl(
                              workspace.data.detail.receiptFileReference ?? selectedItem.receiptFileReference,
                            ) ?? "#"}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Скачать квитанцию
                          </a>
                        </Button>
                      </div>
                    ) : null}
                  </div>
                  {!selectedPrimaryAction ? <Badge variant="outline">Нет доступных действий</Badge> : null}
                  <div className="flex flex-wrap gap-2">
                    {selectedItem.capabilities.map((capability) => (
                      <Button
                        key={capability.key}
                        size="sm"
                        variant={capability.key === selectedPrimaryAction?.key ? "primary" : capability.key === "cancel" ? "danger" : "secondary"}
                        loading={action.isPending}
                        onClick={() =>
                          action.mutate({ submissionId: selectedItem.id, actionKey: capability.key })
                        }
                      >
                        {capability.label}
                      </Button>
                    ))}
                  </div>
                  <Textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="Комментарий к текущему действию"
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      loading={action.isPending}
                      onClick={() =>
                        action.mutate({
                          submissionId: selectedItem.id,
                          actionKey: "request_missing_files",
                        })
                      }
                    >
                      Запросить недостающие файлы
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      loading={action.isPending}
                      onClick={() =>
                        action.mutate({
                          submissionId: selectedItem.id,
                          actionKey: "add_internal_note",
                        })
                      }
                    >
                      Добавить внутреннюю заметку
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      loading={action.isPending}
                      onClick={() =>
                        action.mutate({
                          submissionId: selectedItem.id,
                          actionKey: "send_participant_message",
                        })
                      }
                    >
                      Сообщение участнику
                    </Button>
                  </div>
                  <Tabs defaultValue="overview">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="overview">Обзор</TabsTrigger>
                      <TabsTrigger value="timeline">История</TabsTrigger>
                      <TabsTrigger value="communication">Коммуникация</TabsTrigger>
                    </TabsList>
                    <TabsContent value="overview" className="space-y-2">
                      <div className="rounded-md border p-2 text-sm">
                        <p className="font-medium">Выступления в заявке</p>
                        {(workspace.data.detail.performances ?? []).length === 0 ? (
                          <p className="text-muted-foreground text-xs">Нет выступлений</p>
                        ) : (
                          <div className="space-y-2">
                            {(workspace.data.detail.performances ?? []).map((performance) => (
                              <Card key={performance.submissionId}>
                                <button
                                  type="button"
                                  className="flex w-full items-center justify-between gap-3 p-3 text-left cursor-pointer"
                                  onClick={() =>
                                    setOpenPerformances((prev) => ({
                                      ...prev,
                                      [performance.submissionId]: !prev[performance.submissionId],
                                    }))
                                  }
                                >
                                  <div className="flex min-w-0 flex-1 items-center gap-2">
                                    {openPerformances[performance.submissionId] ? (
                                      <ChevronUp className="size-4 shrink-0" />
                                    ) : (
                                      <ChevronDown className="size-4 shrink-0" />
                                    )}
                                    <div className="min-w-0">
                                      <p className="truncate text-xs font-medium">
                                        #{performance.submissionId.slice(0, 8).toUpperCase()} · {performance.title}
                                      </p>
                                      <p className="mt-1 text-xs text-muted-foreground">
                                        Участников: {performance.participantsCount ?? 0} · Педагогов: {performance.teachersCount ?? 0}
                                      </p>
                                    </div>
                                  </div>
                                  <Badge variant="secondary">{statusLabel(performance.status)}</Badge>
                                </button>
                                {openPerformances[performance.submissionId] ? (
                                  <CardContent className="border-t border-border pt-3">
                                    <div className="space-y-1">
                                  <p className="text-xs text-muted-foreground">
                                    Номинация: {performance.nominationName ?? "—"} · Дисциплина: {performance.disciplineName ?? "—"}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    Возраст: {performance.ageCategoryName ?? "—"} · Группа: {performance.participantGroupName ?? "—"}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    Формат: {performance.participationFormatName ?? "—"} · Длительность:{" "}
                                    {performance.durationSeconds ?? 0} сек
                                  </p>
                                  <div className="mt-1 space-y-1">
                                    <p className="text-xs font-medium">Участники</p>
                                    {(performance.participants ?? []).length === 0 ? (
                                      <p className="text-xs text-muted-foreground">Нет данных</p>
                                    ) : (
                                      (performance.participants ?? []).map((participant) => (
                                        <p key={participant.id} className="text-xs text-muted-foreground">
                                          {participant.name} · участников: {participant.memberCount}
                                        </p>
                                      ))
                                    )}
                                  </div>
                                  <div className="mt-1 space-y-1">
                                    <p className="text-xs font-medium">Педагоги</p>
                                    {(performance.teachers ?? []).length === 0 ? (
                                      <p className="text-xs text-muted-foreground">Нет данных</p>
                                    ) : (
                                      (performance.teachers ?? []).map((teacher) => (
                                        <p key={teacher.id} className="text-xs text-muted-foreground">
                                          {teacher.name} · {teacher.role}
                                        </p>
                                      ))
                                    )}
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    Сумма номера:{" "}
                                    {performance.priceAmount
                                      ? `${performance.priceAmount} ${performance.priceCurrency ?? "BYN"}`
                                      : "не рассчитана"}
                                  </p>
                                  {(performance.attachments ?? []).length === 0 ? (
                                    <p className="mt-1 text-xs text-muted-foreground">Файлы не загружены</p>
                                  ) : (
                                    <div className="mt-2 flex flex-wrap gap-2">
                                      {(performance.attachments ?? []).map((file) => (
                                        <Button key={file.id} asChild size="sm" variant="outline">
                                          <a href={receiptDownloadUrl(file.fileReference) ?? "#"} target="_blank" rel="noreferrer">
                                            Скачать: {attachmentTypeLabel(file.type)}
                                          </a>
                                        </Button>
                                      ))}
                                    </div>
                                  )}
                                    </div>
                                  </CardContent>
                                ) : null}
                              </Card>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="rounded-md border p-2 text-sm">
                        <p className="font-medium">Оплата</p>
                        <p className="text-xs text-muted-foreground">
                          Статус: {paymentStatusLabel(selectedItem.paymentStatus)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Сумма по заявке:{" "}
                          {workspace.data.detail.totalPriceAmount
                            ? `${workspace.data.detail.totalPriceAmount} ${workspace.data.detail.totalPriceCurrency ?? "BYN"}`
                            : "не рассчитана"}
                        </p>
                        {receiptDownloadUrl(workspace.data.detail.receiptFileReference ?? selectedItem.receiptFileReference) ? (
                          <div className="mt-2">
                            <Button asChild size="sm" variant="outline">
                              <a
                                href={receiptDownloadUrl(
                                  workspace.data.detail.receiptFileReference ?? selectedItem.receiptFileReference,
                                ) ?? "#"}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Скачать квитанцию
                              </a>
                            </Button>
                          </div>
                        ) : (
                          <p className="mt-1 text-xs text-muted-foreground">Файл квитанции еще не прикреплен.</p>
                        )}
                      </div>
                      <div className="rounded-md border p-2 text-sm">
                        <p className="font-medium">Файлы</p>
                        {(workspace.data.detail.attachments ?? []).length === 0 ? (
                          <p className="text-muted-foreground text-xs">Нет загруженных файлов</p>
                        ) : (
                          (workspace.data.detail.attachments ?? []).map((attachment) => (
                            <div key={attachment.id} className="flex items-center justify-between gap-2 py-1">
                              <p className="text-xs text-muted-foreground">
                                {attachmentTypeLabel(attachment.type)} · {attachment.fileReference}
                              </p>
                              <Button asChild size="sm" variant="outline">
                                <a href={receiptDownloadUrl(attachment.fileReference) ?? "#"} target="_blank" rel="noreferrer">
                                  Скачать
                                </a>
                              </Button>
                            </div>
                          ))
                        )}
                      </div>
                    </TabsContent>
                    <TabsContent value="timeline" className="space-y-2">
                      <p className="font-medium text-sm">Таймлайн</p>
                      {workspace.data.detail.timeline.map((event) => (
                        <div key={`${event.kind}-${event.at}`} className="rounded-md border p-2 text-sm">
                          <p>{event.label}</p>
                          <p className="text-muted-foreground text-xs">{new Date(event.at).toLocaleString()}</p>
                        </div>
                      ))}
                      <p className="pt-2 font-medium text-sm">Журнал аудита</p>
                      {(workspace.data.detail.audit ?? []).length === 0 ? (
                        <p className="text-sm text-muted-foreground">Записей пока нет.</p>
                      ) : (
                        (workspace.data.detail.audit ?? []).map((event) => (
                          <div key={`${event.by}-${event.at}`} className="rounded-md border p-2 text-sm">
                            <p>{event.reason}</p>
                            <p className="text-muted-foreground text-xs">{event.by}</p>
                          </div>
                        ))
                      )}
                    </TabsContent>
                    <TabsContent value="communication" className="space-y-2">
                      <p className="font-medium text-sm">Внутренние заметки</p>
                      {(workspace.data.detail.internalNotes ?? []).map((entry: { text: string; created_at: string }) => (
                        <div key={`${entry.created_at}-${entry.text}`} className="rounded-md border p-2 text-sm">
                          <p>{entry.text}</p>
                          <p className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</p>
                        </div>
                      ))}
                      <p className="pt-2 font-medium text-sm">Сообщения участнику</p>
                      {(workspace.data.detail.participantMessages ?? []).map(
                        (entry: { text: string; created_at: string }) => (
                          <div key={`${entry.created_at}-${entry.text}`} className="rounded-md border p-2 text-sm">
                            <p>{entry.text}</p>
                            <p className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</p>
                          </div>
                        ),
                      )}
                    </TabsContent>
                  </Tabs>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </PageContainer>
  );
}
