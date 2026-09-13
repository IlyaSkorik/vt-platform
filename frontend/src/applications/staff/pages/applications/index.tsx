import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, FileArchive } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { resolveMediaUrl } from "@/features/competitions/lib/media-url";
import { apiClient, humanMessage } from "@/shared/api";
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
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Select,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from "@/shared/ui";

type Capability = { key: string; label: string };
type Queue = { key: string; label: string; count: number };
type Item = {
  id: string;
  applicationId?: string | null;
  applicationNumber: string;
  competition: string;
  /** Кто выступает: ФИО солиста или название коллектива — не идентификатор. */
  applicant: string;
  /** Когда заявку подали, ISO-строкой; у старых записей может не быть. */
  submissionDate?: string | null;
  /** Жанр номера — название, а не идентификатор: по нему же идёт фильтр. */
  nomination?: string | null;
  /** Хронометраж номера в секундах; складывается в итог по жанру. */
  durationSeconds?: number;
  performancesCount: number;
  participantsCount: number;
  status: string;
  queue: string;
  paymentStatus: string;
  hasReceipt?: boolean;
  /** Every slip the order paid with — a fee settled in instalments has several. */
  receiptFileReferences?: string[];
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
    comment?: string | null;
    ageComposition?: string | null;
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
  receiptFileReferences?: string[];
  /** Кто указан стороной договора по заявке — только у фестивалей, которые это собирают. */
  payerName?: string | null;
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
  competitions?: Array<{ id: string; title: string; status: string }>;
  /** Жанры, которые реально встречаются в выбранном фестивале. */
  nominations?: string[];
  applications: Item[];
  selected: string | null;
  detail: Detail | null;
  metrics: Record<string, number>;
};

async function fetchWorkspace(
  queue: string,
  q: string,
  selected: string | null,
  filters: Record<string, string>,
): Promise<Workspace> {
  const search = new URLSearchParams();
  if (queue) search.set("queue", queue);
  if (q) search.set("q", q);
  if (selected) search.set("selected", selected);
  for (const [key, value] of Object.entries(filters)) {
    if (value) search.set(key, value);
  }
  const response = await apiClient.get(`staff/applications/workspace?${search.toString()}`);
  const body = (await response.json()) as { data: Workspace };
  return body.data;
}

async function runAction(
  submissionId: string,
  action: string,
  comment: string,
  missingTypes: string[] = [],
): Promise<void> {
  const payload: Record<string, unknown> = { comment };
  if (action === "request_missing_files") {
    payload.types = missingTypes;
  }
  try {
    await apiClient.post(`staff/applications/${submissionId}/actions/${action}`, { json: payload });
  } catch (error) {
    const response = (error as { response?: Response })?.response;
    if (response) {
      const body = (await response.json().catch(() => null)) as {
        detail?: string;
        title?: string;
        message?: string;
        error?: string;
      } | null;
      throw new Error(
        humanMessage(body?.detail ?? body?.message ?? body?.error ?? body?.title, response.status),
      );
    }
    throw error;
  }
}

async function runBulk(action: string, ids: string[], comment: string): Promise<void> {
  await apiClient.post("staff/applications/bulk", { json: { action, ids, comment } });
}

function primaryAction(capabilities: Capability[]): Capability | null {
  const preferred = capabilities.find((item) => item.key !== "cancel");
  return preferred ?? capabilities[0] ?? null;
}

/**
 * Statuses whose cancellation is worth a second click.
 *
 * The entry is in the running order: the applicant cannot undo this, CANCELLED is
 * terminal, and documents for the performance may already have been issued. Earlier
 * in the lifecycle a cancellation is routine and stays a single click.
 */
const CANCEL_NEEDS_CONFIRMATION = new Set(["ACCEPTED", "SCHEDULED"]);

/**
 * Значение пункта «снять фильтр».
 *
 * Пустая строка здесь не годится: Radix считает её отсутствием выбора и на таком
 * пункте падает. Та же подмена уже сделана в фильтрах прайсинга и правил допуска.
 */
const FILTER_ALL = "__all__";

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
    SCHEDULED: "На фестивале",
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

/**
 * The API hands back a ready address for every stored file — an absolute bucket URL,
 * or a `/media/…` path when the files still sit on the API host's disk. Only the
 * second shape needs an origin, which is all `resolveMediaUrl` adds. Guessing the
 * prefix here (the old shape of this function) is what made every receipt 404 once
 * the uploads moved to a bucket.
 */
function fileHref(reference: string | null | undefined): string | null {
  return resolveMediaUrl(reference);
}

/**
 * Links to every receipt the order paid with.
 *
 * A fee is regularly settled by more than one transfer, so a single link would
 * hide the rest of the payment from whoever is reconciling it. The slips are
 * numbered only when there is more than one — numbering a lone receipt reads as
 * a second one gone missing.
 *
 * The label says «Открыть», not «Скачать»: the link opens the slip in a new tab
 * and saving it is a separate decision the browser leaves to the organizer.
 */
function ReceiptLinks({ references }: { references: string[] }): React.JSX.Element | null {
  const urls = references.map(fileHref).filter((url): url is string => url !== null);
  if (urls.length === 0) {
    return null;
  }
  return (
    <div className="mt-2 flex flex-wrap justify-end gap-2">
      {urls.map((url, index) => (
        <Button asChild key={url} size="sm" variant="outline">
          <a href={url} target="_blank" rel="noreferrer">
            {urls.length === 1 ? "Открыть квитанцию" : `Открыть квитанцию ${index + 1}`}
          </a>
        </Button>
      ))}
    </div>
  );
}

function attachmentTypeLabel(type: string): string {
  const map: Record<string, string> = {
    MUSIC: "Музыка",
    VIDEO: "Видео",
    DOCUMENT: "Документ",
    BENEFIT: "Документ о льготе",
    RECEIPT: "Квитанция",
    OTHER: "Файл",
  };
  return map[type] ?? type;
}

/**
 * Когда заявку подали — датой и временем, без секунд.
 *
 * Время здесь не украшение: две заявки одного коллектива различают именно по нему,
 * и порядок подачи решает, чью очередь разбирают первой.
 */
function submittedAtLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Хронометраж как «3 мин 30 с», а для итога по жанру — «2 ч 05 мин 30 с».
 *
 * Одна и та же запись и для номера, и для суммы: организатор сравнивает их между
 * собой, верстая блок в расписании, и разные форматы рядом пришлось бы пересчитывать
 * в уме. Часы появляются, только когда есть; секунды остаются всегда — из номеров
 * по 2:30 час набирается ровно на них.
 */
function durationLabel(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts =
    hours > 0 ? [`${hours} ч`, `${String(minutes).padStart(2, "0")} мин`] : [`${minutes} мин`];
  return [...parts, `${String(seconds).padStart(2, "0")} с`].join(" ");
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

/**
 * Download the orders' paperwork — receipts and benefit certificates — as one ZIP.
 *
 * Kept apart from the programme's backing-track archive on purpose: this is the
 * bundle somebody reconciles payments against, and it must not drag a festival's
 * audio along with it. Follows the competition filter above, so what is downloaded
 * is what is on screen.
 *
 * Fetched rather than linked because the endpoint is staff-gated and a plain
 * `<a href>` would arrive without the token.
 */
function DocumentsArchiveButton({ competitionId }: { competitionId: string }): React.JSX.Element {
  const [busy, setBusy] = useState(false);

  const download = async () => {
    setBusy(true);
    try {
      const query = competitionId ? `?competitionId=${encodeURIComponent(competitionId)}` : "";
      const response = await apiClient.get(`staff/applications/documents.zip${query}`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = "Документы заявок.zip";
      document.body.append(link);
      link.click();
      link.remove();
      // Revoking immediately can cancel the download in some browsers; a tick is enough.
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex justify-end">
      <Button variant="outline" size="sm" loading={busy} onClick={() => void download()}>
        <FileArchive className="size-4" /> Скачать документы
      </Button>
    </div>
  );
}

export function StaffApplicationsProcessingPage(): React.JSX.Element {
  // A deep link (e.g. "Открыть заявку" from the participant registry) may seed the
  // queue, competition and preselected submission via the URL; otherwise defaults apply.
  const [searchParams] = useSearchParams();
  const [queue, setQueue] = useState(() => searchParams.get("queue") ?? "NEW");
  const [q, setQ] = useState(() => searchParams.get("q") ?? "");
  const [selected, setSelected] = useState<string | null>(() => searchParams.get("selected"));
  const [comment, setComment] = useState("");
  const [selectedMissingTypes, setSelectedMissingTypes] = useState<string[]>([]);
  const [competitionId, setCompetitionId] = useState(() => searchParams.get("competitionId") ?? "");
  const [nomination, setNomination] = useState(() => searchParams.get("nomination") ?? "");
  const [openPerformances, setOpenPerformances] = useState<Record<string, boolean>>({});
  const [actionError, setActionError] = useState<string | null>(null);
  // Set once the organizer has clicked «Отменить» on an entry already in the running
  // order, so the second click is the deliberate one. See `needsCancelConfirmation`.
  const [cancelArmed, setCancelArmed] = useState(false);
  const queryClient = useQueryClient();

  const workspace = useQuery({
    queryKey: ["staff", "applications", "workspace", queue, q, selected, competitionId, nomination],
    queryFn: () =>
      fetchWorkspace(queue, q, selected, {
        competitionId,
        nomination,
      }),
    placeholderData: (previousData) => previousData,
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
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
      const better =
        statusPriority(item.status) < statusPriority(existing.status) ? item : existing;
      // Заявку подали один раз, а номеров в ней несколько: датой заказа считаем
      // самый ранний номер, иначе карточка «омолаживалась» бы при каждой правке.
      const earliest = [existing.submissionDate, item.submissionDate]
        .filter((value): value is string => Boolean(value))
        .sort()[0];
      map.set(key, {
        ...better,
        submissionDate: earliest ?? null,
        performancesCount: existing.performancesCount + item.performancesCount,
        participantsCount: existing.participantsCount + item.participantsCount,
      });
    }
    return Array.from(map.values());
  }, [inbox]);

  // Считаем выступления, а не заявки: заявка может держать номера в разных жанрах,
  // и при фильтре по одному из них она целиком в счёт не идёт. Единица жанра —
  // номер, и хронометраж складывается из тех же строк.
  const filteredTotals = useMemo(
    () => ({
      performances: inbox.length,
      durationSeconds: inbox.reduce((total, item) => total + (item.durationSeconds ?? 0), 0),
    }),
    [inbox],
  );

  const action = useMutation({
    mutationFn: ({ submissionId, actionKey }: { submissionId: string; actionKey: string }) =>
      runAction(submissionId, actionKey, comment, selectedMissingTypes),
    onSuccess: async () => {
      const next = nextId(groupedInbox, selectedItem?.id ?? null);
      setComment("");
      setSelectedMissingTypes([]);
      setActionError(null);
      setSelected(next);
      await queryClient.invalidateQueries({ queryKey: ["staff", "applications", "workspace"] });
    },
    onError: (error) => {
      setActionError(error instanceof Error ? error.message : "Не удалось выполнить действие.");
    },
  });
  const bulkReminder = useMutation({
    mutationFn: ({ ids, actionKey }: { ids: string[]; actionKey: string }) =>
      runBulk(actionKey, ids, comment),
    onSuccess: async () => {
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

  // Список жанров зависит от выбранного фестиваля: унесённый с прошлого фестиваля
  // фильтр не находит ничего и выглядит как пустая очередь.
  useEffect(() => {
    const available = workspace.data?.nominations;
    if (!available || !nomination) return;
    if (!available.includes(nomination)) setNomination("");
  }, [workspace.data?.nominations, nomination]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: сбрасываем раскрытые выступления при смене выбранной заявки
  useEffect(() => {
    setOpenPerformances({});
    // A primed cancellation must never carry over to another entry.
    setCancelArmed(false);
  }, [selected]);

  function executeAction(actionKey: string): void {
    const requiresComment =
      actionKey === "return_for_correction" ||
      actionKey === "request_missing_files" ||
      actionKey === "add_internal_note";
    if (requiresComment && !comment.trim()) {
      if (actionKey === "add_internal_note") {
        setActionError("Введите текст внутренней заметки.");
      } else {
        setActionError("Введите комментарий для участника перед выполнением действия.");
      }
      return;
    }
    if (actionKey === "request_missing_files" && selectedMissingTypes.length === 0) {
      setActionError("Выберите, какие именно файлы нужно прикрепить.");
      return;
    }
    if (!selectedItem) return;
    if (needsCancelConfirmation(actionKey) && !cancelArmed) {
      setCancelArmed(true);
      setActionError(null);
      return;
    }
    setActionError(null);
    setCancelArmed(false);
    action.mutate({ submissionId: selectedItem.id, actionKey });
  }

  /** Whether this action is the cancellation of an entry already in the competition. */
  function needsCancelConfirmation(actionKey: string): boolean {
    return actionKey === "cancel" && CANCEL_NEEDS_CONFIRMATION.has(selectedItem?.status ?? "");
  }

  if (!workspace.data) {
    return <LoadingState label="Загружаем пространство обработки заявок..." />;
  }

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Обработка заявок</PageTitle>
        <PageDescription>
          Режим задач: берите следующую заявку, выполняйте действие, переходите дальше.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="space-y-3">
          <Card>
            <CardContent className="pt-6  ">
              <div className="flex flex-wrap gap-2">
                {workspace.data.queues.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setQueue(item.key)}
                    className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition ${
                      queue === item.key
                        ? "border-primary bg-primary/10 text-primary"
                        : "hover:border-primary/50"
                    }`}
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
                {queue === "WAITING_PAYMENT" ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={groupedInbox.length === 0}
                    loading={bulkReminder.isPending}
                    onClick={() =>
                      bulkReminder.mutate({
                        ids: groupedInbox.map((item) => item.id),
                        actionKey: "send_payment_reminder",
                      })
                    }
                  >
                    Отправить всем напоминание об оплате
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex flex-col gap-2 pt-4">
              <div className="grid gap-2 md:grid-cols-3">
                <Input
                  value={q}
                  onChange={(event) => setQ(event.target.value)}
                  placeholder="Поиск по номеру/заявителю"
                />
                <Select
                  placeholder="Фильтр по фестивалю"
                  value={competitionId}
                  onValueChange={(value) => setCompetitionId(value)}
                  options={(workspace.data.competitions ?? []).map((item) => ({
                    value: item.id,
                    label: item.title,
                  }))}
                />
                <Select
                  placeholder="Фильтр по жанру"
                  value={nomination || FILTER_ALL}
                  onValueChange={(value) => setNomination(value === FILTER_ALL ? "" : value)}
                  options={[
                    { value: FILTER_ALL, label: "Все жанры" },
                    ...(workspace.data.nominations ?? []).map((item) => ({
                      value: item,
                      label: item,
                    })),
                  ]}
                />
              </div>
              {/* Ради этой строки жанр и фильтруют: по ней верстают блок в
                  расписании, где считают номера и минуты, а не заявки. */}
              <p className="text-sm text-muted-foreground">
                {nomination ? `Жанр «${nomination}»` : "Отобрано"}: выступлений —{" "}
                <span className="font-medium text-foreground">{filteredTotals.performances}</span> ·
                общее время —{" "}
                <span className="font-medium text-foreground">
                  {durationLabel(filteredTotals.durationSeconds)}
                </span>
              </p>
              <DocumentsArchiveButton competitionId={competitionId} />
            </CardContent>
          </Card>
        </div>
        <div className="mt-3 grid gap-4 xl:grid-cols-[360px_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>Входящие заявки</CardTitle>
              <CardDescription>
                {groupedInbox.length === 0
                  ? "Очередь пуста"
                  : `Всего заявок в очереди: ${groupedInbox.length}`}
              </CardDescription>
            </CardHeader>
            <CardContent className="max-h-[65vh] space-y-2 overflow-auto [scrollbar-color:var(--border-default)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:w-2">
              {groupedInbox.map((item) => {
                const isSelected = item.id === selected;
                const submittedAt = submittedAtLabel(item.submissionDate);
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-current={isSelected}
                    onClick={() => setSelected(item.id)}
                    // Очередь и рабочая карточка стоят рядом, и без подсветки
                    // непонятно, какую именно заявку сейчас разбирают.
                    className={`w-full cursor-pointer rounded-md border p-3 text-left transition ${
                      isSelected ? "border-primary bg-primary/10" : "hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">#{item.applicationNumber}</p>
                      <Badge>{statusLabel(item.status)}</Badge>
                    </div>
                    <p className="text-sm font-medium">{item.applicant}</p>
                    <p className="text-sm text-muted-foreground">{item.competition}</p>
                    <p className="text-sm text-muted-foreground">
                      Номеров: {item.performancesCount} · Участников: {item.participantsCount}
                    </p>
                    {submittedAt ? (
                      <p className="text-xs text-muted-foreground">Подана: {submittedAt}</p>
                    ) : null}
                  </button>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Рабочая карточка</CardTitle>
              <CardDescription>
                Минимум кликов: одно главное действие и контекст рядом.
              </CardDescription>
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
                      Статус:{" "}
                      <span className="font-medium text-foreground">
                        {statusLabel(selectedItem.status)}
                      </span>
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
                    {/* Заказчик — строкой рядом с оплатой: по нему оформляют договор
                        и счёт, и его же ищут, когда приходит перевод. */}
                    {workspace.data.detail.payerName ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        Заказчик:{" "}
                        <span className="font-medium text-foreground">
                          {workspace.data.detail.payerName}
                        </span>
                      </p>
                    ) : null}
                    <ReceiptLinks
                      references={
                        workspace.data.detail.receiptFileReferences ??
                        selectedItem.receiptFileReferences ??
                        []
                      }
                    />
                  </div>
                  {!selectedPrimaryAction ? (
                    <Badge variant="outline">Нет доступных действий</Badge>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    {selectedItem.capabilities.map((capability) => (
                      <Button
                        key={capability.key}
                        size="sm"
                        // Cancelling always reads as destructive, even where it is the
                        // only action left and would otherwise be styled as primary.
                        variant={
                          capability.key === "cancel"
                            ? "danger"
                            : capability.key === selectedPrimaryAction?.key
                              ? "primary"
                              : "secondary"
                        }
                        loading={action.isPending}
                        onClick={() => executeAction(capability.key)}
                      >
                        {capability.key === "cancel" && cancelArmed
                          ? "Подтвердить отмену"
                          : capability.label}
                      </Button>
                    ))}
                  </div>
                  {cancelArmed ? (
                    <p className="text-sm text-warning">
                      Заявка уже на фестивале. Отмена необратима, участник вернуть её не сможет, а
                      выданные по ней документы останутся в реестре. Нажмите «Подтвердить отмену»,
                      чтобы продолжить.
                    </p>
                  ) : null}
                  <Textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="Комментарий к текущему действию"
                  />
                  <div className="flex flex-wrap gap-2">
                    {[
                      { key: "MUSIC", label: "Музыка" },
                      { key: "VIDEO", label: "Видео" },
                      { key: "DOCUMENT", label: "Документы" },
                      { key: "RECEIPT", label: "Квитанция" },
                      { key: "OTHER", label: "Другое" },
                    ].map((type) => {
                      const selected = selectedMissingTypes.includes(type.key);
                      return (
                        <button
                          key={type.key}
                          type="button"
                          onClick={() =>
                            setSelectedMissingTypes((prev) =>
                              prev.includes(type.key)
                                ? prev.filter((item) => item !== type.key)
                                : [...prev, type.key],
                            )
                          }
                          className={`rounded-md border px-2 py-1 text-xs transition ${
                            selected
                              ? "cursor-pointer border-primary bg-primary/10 text-primary"
                              : "cursor-pointer hover:border-primary/50"
                          }`}
                        >
                          {type.label}
                        </button>
                      );
                    })}
                  </div>
                  {actionError ? <p className="text-sm text-danger">{actionError}</p> : null}
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      loading={action.isPending}
                      onClick={() => executeAction("request_missing_files")}
                    >
                      Запросить недостающие файлы
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      loading={action.isPending}
                      onClick={() => executeAction("add_internal_note")}
                    >
                      Добавить внутреннюю заметку
                    </Button>
                  </div>
                  <Tabs defaultValue="overview">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="overview" className="cursor-pointer">
                        Обзор
                      </TabsTrigger>
                      <TabsTrigger value="timeline" className="cursor-pointer">
                        История
                      </TabsTrigger>
                      <TabsTrigger value="communication" className="cursor-pointer">
                        Коммуникация
                      </TabsTrigger>
                    </TabsList>
                    <TabsContent value="overview" className="space-y-2">
                      <div className="rounded-md border p-2 text-sm">
                        <p className="font-medium mb-2">Выступления в заявке</p>
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
                                        #{performance.submissionId.slice(0, 8).toUpperCase()} ·{" "}
                                        {performance.title}
                                      </p>
                                      <p className="mt-1 text-xs text-muted-foreground">
                                        Участников: {performance.participantsCount ?? 0} ·
                                        Педагогов: {performance.teachersCount ?? 0}
                                      </p>
                                    </div>
                                  </div>
                                  <Badge variant="secondary">
                                    {statusLabel(performance.status)}
                                  </Badge>
                                </button>
                                {openPerformances[performance.submissionId] ? (
                                  <CardContent className="border-t border-border pt-3">
                                    <div className="space-y-1">
                                      <p className="text-xs text-muted-foreground">
                                        Жанр: {performance.nominationName ?? "—"} · Номинация:{" "}
                                        {performance.disciplineName ?? "—"}
                                      </p>
                                      <p className="text-xs text-muted-foreground">
                                        Возраст: {performance.ageCategoryName ?? "—"} · Группа:{" "}
                                        {performance.participantGroupName ?? "—"}
                                      </p>
                                      {/* Смешанную категорию участник расшифровывает
                                          сам — без этого номер не подать. */}
                                      {performance.ageComposition?.trim() ? (
                                        <p className="text-xs text-muted-foreground">
                                          Возрастной состав: {performance.ageComposition.trim()}
                                        </p>
                                      ) : null}
                                      <p className="text-xs text-muted-foreground">
                                        Формат: {performance.participationFormatName ?? "—"} ·
                                        Длительность:{" "}
                                        {durationLabel(performance.durationSeconds ?? 0)}
                                      </p>
                                      {performance.comment?.trim() ? (
                                        <div className="mt-1 space-y-1">
                                          <p className="text-xs font-medium">
                                            Дополнительная информация
                                          </p>
                                          <p className="whitespace-pre-line text-xs text-muted-foreground">
                                            {performance.comment.trim()}
                                          </p>
                                        </div>
                                      ) : null}
                                      <div className="mt-1 space-y-1">
                                        <p className="text-xs font-medium">Участники</p>
                                        {(performance.participants ?? []).length === 0 ? (
                                          <p className="text-xs text-muted-foreground">
                                            Нет данных
                                          </p>
                                        ) : (
                                          (performance.participants ?? []).map((participant) => (
                                            <p
                                              key={participant.id}
                                              className="text-xs text-muted-foreground"
                                            >
                                              {participant.name} · участников:{" "}
                                              {participant.memberCount}
                                            </p>
                                          ))
                                        )}
                                      </div>
                                      <div className="mt-1 space-y-1">
                                        <p className="text-xs font-medium">Педагоги</p>
                                        {(performance.teachers ?? []).length === 0 ? (
                                          <p className="text-xs text-muted-foreground">
                                            Нет данных
                                          </p>
                                        ) : (
                                          (performance.teachers ?? []).map((teacher) => (
                                            <p
                                              key={teacher.id}
                                              className="text-xs text-muted-foreground"
                                            >
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
                                        <p className="mt-1 text-xs text-muted-foreground">
                                          Файлы не загружены
                                        </p>
                                      ) : (
                                        <div className="mt-2 flex flex-wrap gap-2">
                                          {(performance.attachments ?? []).map((file) => (
                                            <Button
                                              key={file.id}
                                              asChild
                                              size="sm"
                                              variant="outline"
                                            >
                                              <a
                                                href={fileHref(file.fileReference) ?? "#"}
                                                target="_blank"
                                                rel="noreferrer"
                                              >
                                                Открыть: {attachmentTypeLabel(file.type)}
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
                        {(
                          workspace.data.detail.receiptFileReferences ??
                          selectedItem.receiptFileReferences ??
                          []
                        ).length > 0 ? (
                          <ReceiptLinks
                            references={
                              workspace.data.detail.receiptFileReferences ??
                              selectedItem.receiptFileReferences ??
                              []
                            }
                          />
                        ) : (
                          <p className="mt-1 text-xs text-muted-foreground">
                            Файл квитанции еще не прикреплен.
                          </p>
                        )}
                      </div>
                      <div className="rounded-md border p-2 text-sm">
                        <p className="font-medium">Файлы</p>
                        {(workspace.data.detail.attachments ?? []).length === 0 ? (
                          <p className="text-muted-foreground text-xs">Нет загруженных файлов</p>
                        ) : (
                          (workspace.data.detail.attachments ?? []).map((attachment) => (
                            <div
                              key={attachment.id}
                              className="flex items-center justify-between gap-2 py-1"
                            >
                              <p className="text-xs text-muted-foreground">
                                {attachmentTypeLabel(attachment.type)} · {attachment.fileReference}
                              </p>
                              <Button asChild size="sm" variant="outline">
                                <a
                                  href={fileHref(attachment.fileReference) ?? "#"}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Открыть
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
                        <div
                          key={`${event.kind}-${event.at}-${event.label}`}
                          className="rounded-md border p-2 text-sm"
                        >
                          <p>{event.label}</p>
                          <p className="text-muted-foreground text-xs">
                            {new Date(event.at).toLocaleString()}
                          </p>
                        </div>
                      ))}
                      <p className="pt-2 font-medium text-sm">Журнал аудита</p>
                      {(workspace.data.detail.audit ?? []).length === 0 ? (
                        <p className="text-sm text-muted-foreground">Записей пока нет.</p>
                      ) : (
                        (workspace.data.detail.audit ?? []).map((event) => (
                          <div
                            key={`${event.by}-${event.at}-${event.reason}`}
                            className="rounded-md border p-2 text-sm"
                          >
                            <p>{event.reason}</p>
                            <p className="text-muted-foreground text-xs">{event.by}</p>
                          </div>
                        ))
                      )}
                    </TabsContent>
                    <TabsContent value="communication" className="space-y-2">
                      <p className="font-medium text-sm">Внутренние заметки</p>
                      {(workspace.data.detail.internalNotes ?? []).map(
                        (entry: { text: string; created_at: string }) => (
                          <div
                            key={`${entry.created_at}-${entry.text}`}
                            className="rounded-md border p-2 text-sm"
                          >
                            <p>{entry.text}</p>
                            <p className="text-muted-foreground text-xs">
                              {new Date(entry.created_at).toLocaleString()}
                            </p>
                          </div>
                        ),
                      )}
                      <p className="pt-2 font-medium text-sm">Сообщения участнику</p>
                      {(workspace.data.detail.participantMessages ?? []).map(
                        (entry: { text: string; created_at: string }) => (
                          <div
                            key={`${entry.created_at}-${entry.text}`}
                            className="rounded-md border p-2 text-sm"
                          >
                            <p>{entry.text}</p>
                            <p className="text-muted-foreground text-xs">
                              {new Date(entry.created_at).toLocaleString()}
                            </p>
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
