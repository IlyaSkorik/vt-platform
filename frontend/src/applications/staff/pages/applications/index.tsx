import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { apiClient } from "@/shared/api";
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
  applicationNumber: string;
  competition: string;
  applicant: string;
  performancesCount: number;
  participantsCount: number;
  status: string;
  queue: string;
  paymentStatus: string;
  capabilities: Capability[];
};
type Detail = {
  id: string;
  status: string;
  performance: string | null;
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

async function runAction(submissionId: string, action: string, comment: string): Promise<void> {
  await apiClient.post(`staff/applications/${submissionId}/actions/${action}`, { json: { comment } });
}

export function StaffApplicationsProcessingPage(): React.JSX.Element {
  const [queue, setQueue] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [teacher, setTeacher] = useState("");
  const [organization, setOrganization] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [hasCorrections, setHasCorrections] = useState("");
  const [hasMissingFiles, setHasMissingFiles] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const workspace = useQuery({
    queryKey: [
      "staff",
      "applications",
      "workspace",
      queue,
      q,
      selected,
      teacher,
      organization,
      dateFrom,
      dateTo,
      hasCorrections,
      hasMissingFiles,
    ],
    queryFn: () =>
      fetchWorkspace(queue, q, selected, {
        teacher,
        organization,
        from: dateFrom,
        to: dateTo,
        hasCorrections,
        hasMissingFiles,
      }),
  });

  const action = useMutation({
    mutationFn: ({ submissionId, actionKey }: { submissionId: string; actionKey: string }) =>
      runAction(submissionId, actionKey, comment),
    onSuccess: async () => {
      setComment("");
      await queryClient.invalidateQueries({ queryKey: ["staff", "applications", "workspace"] });
    },
  });
  const bulk = useMutation({
    mutationFn: async (actionKey: string) => {
      await apiClient.post("staff/applications/bulk", {
        json: { action: actionKey, ids: selectedIds, comment },
      });
    },
    onSuccess: async () => {
      setSelectedIds([]);
      await queryClient.invalidateQueries({ queryKey: ["staff", "applications", "workspace"] });
    },
  });

  const selectedItem = useMemo(
    () => workspace.data?.applications.find((item) => item.id === (workspace.data?.selected ?? selected)) ?? null,
    [workspace.data, selected],
  );

  if (workspace.isLoading || !workspace.data) {
    return <LoadingState label="Загружаем пространство обработки заявок..." />;
  }

  const metricLabels: Record<string, string> = {
    needReview: "Требуют проверки",
    needCorrection: "Требуют исправлений",
    needPayment: "Требуют оплаты",
    ready: "Готовы",
    running: "В процессе конкурса",
    completed: "Завершены",
  };

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Обработка заявок</PageTitle>
        <PageDescription>Рабочее пространство организатора: очереди, обработка, история и действия.</PageDescription>
      </PageHeader>
      <PageContent>
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Object.entries(workspace.data.metrics).map(([key, value]) => (
            <Card key={key}>
              <CardHeader className="pb-2">
                <CardDescription>{metricLabels[key] ?? key}</CardDescription>
                <CardTitle className="text-2xl">{value}</CardTitle>
              </CardHeader>
            </Card>
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[280px_1fr_420px]">
          <Card>
            <CardHeader>
              <CardTitle>Очереди</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {workspace.data.queues.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setQueue(item.key === queue ? "" : item.key)}
                  className="flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm"
                >
                  <span>{item.label}</span>
                  <Badge>{item.count}</Badge>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Очередь заявок</CardTitle>
              <Input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Поиск по номеру/конкурсу/заявителю" />
              <div className="grid grid-cols-2 gap-2">
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
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => bulk.mutate("approve")} loading={bulk.isPending}>
                  Массово одобрить
                </Button>
                <Button size="sm" variant="secondary" onClick={() => bulk.mutate("request_payment")} loading={bulk.isPending}>
                  Массово запросить оплату
                </Button>
                <Button size="sm" variant="secondary" onClick={() => bulk.mutate("cancel")} loading={bulk.isPending}>
                  Массово в архив
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href="/api/v1/staff/applications/export?type=applications&format=csv">Экспорт CSV</a>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href="/api/v1/staff/applications/export?type=applications&format=excel">Экспорт Excel</a>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {workspace.data.applications.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelected(item.id)}
                  className="w-full rounded-md border p-3 text-left"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={(event) => {
                          setSelectedIds((prev) =>
                            event.target.checked ? [...prev, item.id] : prev.filter((id) => id !== item.id),
                          );
                        }}
                        onClick={(event) => event.stopPropagation()}
                        className="mr-2"
                      />
                      #{item.applicationNumber}
                    </p>
                    <Badge>{item.status}</Badge>
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
              <CardTitle>Детали обработки</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!workspace.data.detail || !selectedItem ? (
                <p className="text-sm text-muted-foreground">Выберите заявку из очереди.</p>
              ) : (
                <>
                  <div>
                    <p className="font-medium">{selectedItem.competition}</p>
                    <p className="text-sm text-muted-foreground">{workspace.data.detail.performance ?? "Без названия номера"}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedItem.capabilities.map((capability) => (
                      <Button
                        key={capability.key}
                        size="sm"
                        variant={capability.key === "cancel" ? "danger" : "secondary"}
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
                    placeholder="Комментарий для действий (например, причина возврата на исправление)"
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
                  <div>
                    <p className="mb-2 font-medium text-sm">Таймлайн</p>
                    <div className="space-y-2">
                      {workspace.data.detail.timeline.map((event) => (
                        <div key={`${event.kind}-${event.at}`} className="rounded-md border p-2 text-sm">
                          <p>{event.label}</p>
                          <p className="text-muted-foreground text-xs">{new Date(event.at).toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-2 font-medium text-sm">Журнал аудита</p>
                    <div className="space-y-2">
                      {workspace.data.detail.audit.map((event) => (
                        <div key={`${event.by}-${event.at}`} className="rounded-md border p-2 text-sm">
                          <p>{event.reason}</p>
                          <p className="text-muted-foreground text-xs">{event.by}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-2 font-medium text-sm">Внутренние заметки</p>
                    <div className="space-y-2">
                      {(workspace.data.detail.internalNotes ?? []).map((entry: { text: string; created_at: string }) => (
                        <div key={`${entry.created_at}-${entry.text}`} className="rounded-md border p-2 text-sm">
                          <p>{entry.text}</p>
                          <p className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-2 font-medium text-sm">Сообщения участнику</p>
                    <div className="space-y-2">
                      {(workspace.data.detail.participantMessages ?? []).map(
                        (entry: { text: string; created_at: string }) => (
                          <div key={`${entry.created_at}-${entry.text}`} className="rounded-md border p-2 text-sm">
                            <p>{entry.text}</p>
                            <p className="text-muted-foreground text-xs">{new Date(entry.created_at).toLocaleString()}</p>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </PageContent>
    </PageContainer>
  );
}
