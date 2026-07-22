import {
  AlertTriangle,
  Copy,
  GripVertical,
  Pencil,
  Plus,
  Power,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AdditionalServiceFormValues,
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  billingModelLabel,
  buildAdditionalServiceReorderUpdates,
  buildAdditionalServicesStats,
  buildAdditionalServiceWarnings,
  createAdditionalServicePayload,
  duplicateAdditionalServiceDraft,
  emptyAdditionalServiceForm,
  filterAdditionalServices,
  formatServicePrice,
  moveAdditionalServiceIdBefore,
  nextAdditionalServiceSortOrder,
  resolveServiceFormatLabels,
  serviceToFormValues,
  sortAdditionalServices,
  updateAdditionalServicePayload,
  useAddAdditionalServiceMutation,
  useRemoveAdditionalServiceMutation,
  useReorderAdditionalServicesMutation,
  useSetAdditionalServiceEnabledMutation,
  useUpdateAdditionalServiceMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _AdditionalService,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  IconButton,
  Input,
  PageSection,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { AdditionalServiceFormDialog } from "./additional-service-form-dialog";
import { AdditionalServicesSkeleton } from "./additional-services-skeleton";

interface AdditionalServicesSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function AdditionalServicesSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: AdditionalServicesSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";

  const addService = useAddAdditionalServiceMutation();
  const updateService = useUpdateAdditionalServiceMutation();
  const removeService = useRemoveAdditionalServiceMutation();
  const setEnabled = useSetAdditionalServiceEnabledMutation();
  const reorderServices = useReorderAdditionalServicesMutation();

  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [editingItem, setEditingItem] = useState<_AdditionalService | null>(null);
  const [formInitial, setFormInitial] = useState<AdditionalServiceFormValues>(
    emptyAdditionalServiceForm(),
  );
  const [deleteTarget, setDeleteTarget] = useState<_AdditionalService | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const sorted = useMemo(
    () => sortAdditionalServices(competition.additionalServices),
    [competition.additionalServices],
  );
  const filtered = useMemo(
    () => filterAdditionalServices(sorted, search, competition.participationFormats),
    [sorted, search, competition.participationFormats],
  );
  const stats = useMemo(() => buildAdditionalServicesStats(sorted), [sorted]);
  const warnings = useMemo(() => buildAdditionalServiceWarnings(competition), [competition]);
  const preferredFormatIds = useMemo(
    () => competition.participationFormats.filter((item) => item.enabled).map((item) => item.id),
    [competition.participationFormats],
  );

  if (isLoading) {
    return <AdditionalServicesSkeleton />;
  }

  const apiErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof ApiError) {
      return error.problem?.detail ?? fallback;
    }
    return fallback;
  };

  const openCreate = (): void => {
    setFormMode("create");
    setEditingItem(null);
    setFormInitial(emptyAdditionalServiceForm(preferredFormatIds));
    setFormOpen(true);
  };

  const openEdit = (item: _AdditionalService): void => {
    setFormMode("edit");
    setEditingItem(item);
    setFormInitial(serviceToFormValues(item));
    setFormOpen(true);
  };

  const openDuplicate = (item: _AdditionalService): void => {
    setFormMode("create");
    setEditingItem(null);
    setFormInitial(duplicateAdditionalServiceDraft(item));
    setFormOpen(true);
  };

  const handleSubmit = async (values: AdditionalServiceFormValues): Promise<void> => {
    onAutosaveStateChange("saving");
    try {
      if (formMode === "create") {
        await addService.mutateAsync({
          competitionId: competition.id,
          payload: createAdditionalServicePayload(
            values,
            nextAdditionalServiceSortOrder(competition.additionalServices),
          ),
        });
        toast.success("Доп. услуга добавлена");
      } else if (editingItem) {
        await updateService.mutateAsync({
          competitionId: competition.id,
          serviceId: editingItem.id,
          payload: updateAdditionalServicePayload(values, editingItem.sortOrder),
        });
        toast.success("Доп. услуга обновлена");
      }
      setFormOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось сохранить доп. услугу"));
    }
  };

  const handleToggleEnabled = async (item: _AdditionalService): Promise<void> => {
    if (isReadOnly) return;
    onAutosaveStateChange("saving");
    try {
      await setEnabled.mutateAsync({
        competitionId: competition.id,
        serviceId: item.id,
        enabled: !item.enabled,
      });
      toast.success(item.enabled ? "Услуга выключена" : "Услуга включена");
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить статус услуги"));
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      await removeService.mutateAsync({
        competitionId: competition.id,
        serviceId: deleteTarget.id,
      });
      toast.success("Доп. услуга удалена");
      setDeleteTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось удалить доп. услугу"));
    }
  };

  const handleReorder = async (fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId || search.length > 0) return;
    const orderedIds = sorted.map((item) => item.id);
    const reordered = moveAdditionalServiceIdBefore(orderedIds, fromId, toId);
    const updates = buildAdditionalServiceReorderUpdates(reordered, sorted);
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderServices.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок услуг обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок"));
    }
  };

  const hasNoFormats = competition.participationFormats.length === 0;
  const hasNoServices = competition.additionalServices.length === 0;
  const submitting =
    addService.isPending ||
    updateService.isPending ||
    removeService.isPending ||
    setEnabled.isPending ||
    reorderServices.isPending;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Дополнительные услуги доступны только для просмотра.
            </Alert>
          ) : null}

          {hasNoFormats ? (
            <Alert variant="warning" title="Сначала создайте форматы участия">
              Услуга должна быть доступна хотя бы для одного формата участия.
            </Alert>
          ) : null}

          <PageSection
            title="Доп. услуги"
            description="Платные опции (медаль, доставка, диплом, запись) — каждая привязана к выбранным форматам участия."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-base">Услуги</CardTitle>
                  {!isReadOnly && !hasNoServices && !hasNoFormats ? (
                    <Button type="button" size="sm" onClick={openCreate}>
                      <Plus className="size-3.5" aria-hidden="true" />
                      Создать услугу
                    </Button>
                  ) : null}
                </div>

                {!hasNoServices ? (
                  <Input
                    label="Поиск"
                    placeholder="Название, формат, тип оплаты, цена"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {hasNoFormats ? (
                  <EmptyState
                    icon={<Sparkles />}
                    title="Нет форматов участия"
                    description="Создайте форматы, затем добавьте услуги для нужных из них."
                    action={
                      <Button
                        type="button"
                        onClick={() => onNavigateSection("participation-formats")}
                      >
                        К форматам участия
                      </Button>
                    }
                  />
                ) : hasNoServices ? (
                  <EmptyState
                    icon={<Sparkles />}
                    title="Доп. услуги не созданы"
                    description="Добавьте медали, доставку, электронные дипломы и другие опции."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={openCreate}>
                          Создать первую услугу
                        </Button>
                      ) : undefined
                    }
                  />
                ) : filtered.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поисковый запрос." />
                ) : (
                  <ul className="grid gap-3 sm:grid-cols-2" aria-label="Дополнительные услуги">
                    {filtered.map((item) => {
                      const formatLabels = resolveServiceFormatLabels(
                        item,
                        competition.participationFormats,
                      );
                      return (
                        <li
                          key={item.id}
                          draggable={!isReadOnly && search.length === 0}
                          onDragStart={(event) => {
                            event.dataTransfer.effectAllowed = "move";
                            setDraggedId(item.id);
                          }}
                          onDragEnd={() => setDraggedId(null)}
                          onDragOver={(event) => {
                            if (draggedId && search.length === 0) {
                              event.preventDefault();
                            }
                          }}
                          onDrop={(event) => {
                            event.preventDefault();
                            if (draggedId) {
                              void handleReorder(draggedId, item.id);
                            }
                            setDraggedId(null);
                          }}
                          className={cn(
                            "rounded-lg border border-border bg-card p-3 transition-colors",
                            draggedId === item.id && "opacity-50",
                          )}
                        >
                          <div className="flex items-start gap-2">
                            {!isReadOnly && search.length === 0 ? (
                              <span
                                className="mt-0.5 cursor-grab text-muted-foreground active:cursor-grabbing"
                                aria-hidden="true"
                                title="Перетащите для изменения порядка"
                              >
                                <GripVertical className="size-3.5" />
                              </span>
                            ) : null}

                            <div className="min-w-0 flex-1 space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-medium text-sm">{item.name}</p>
                                <Badge variant={item.enabled ? "success" : "secondary"} size="sm">
                                  {item.enabled ? "Включена" : "Выключена"}
                                </Badge>
                                {item.required ? (
                                  <Badge variant="warning" size="sm">
                                    Обязательная
                                  </Badge>
                                ) : null}
                              </div>
                              <p className="font-medium text-sm tabular-nums">
                                {formatServicePrice(item.amount, item.currency)}
                                <span className="ml-2 font-normal text-muted-foreground">
                                  {billingModelLabel(item.billingModel)}
                                </span>
                              </p>
                              {item.description ? (
                                <p className="text-muted-foreground text-sm">{item.description}</p>
                              ) : null}
                              <div className="flex flex-wrap gap-1.5">
                                {formatLabels.map((label) => (
                                  <Badge key={`${item.id}-${label}`} variant="outline" size="sm">
                                    {label}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          </div>

                          {!isReadOnly ? (
                            <div className="mt-3 flex items-center gap-1">
                              <IconButton
                                type="button"
                                size="sm"
                                variant="ghost"
                                aria-label="Редактировать доп. услугу"
                                icon={<Pencil className="size-3" aria-hidden="true" />}
                                onClick={() => openEdit(item)}
                              />
                              <IconButton
                                type="button"
                                size="sm"
                                variant="ghost"
                                aria-label="Дублировать доп. услугу"
                                icon={<Copy className="size-3" aria-hidden="true" />}
                                onClick={() => openDuplicate(item)}
                              />
                              <IconButton
                                type="button"
                                size="sm"
                                variant="ghost"
                                aria-label={item.enabled ? "Выключить услугу" : "Включить услугу"}
                                icon={<Power className="size-3" aria-hidden="true" />}
                                onClick={() => void handleToggleEnabled(item)}
                              />
                              <IconButton
                                type="button"
                                size="sm"
                                variant="ghost"
                                aria-label="Удалить доп. услугу"
                                icon={<Trash2 className="size-3" aria-hidden="true" />}
                                onClick={() => setDeleteTarget(item)}
                              />
                            </div>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardContent>
            </Card>
          </PageSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <Card className="shadow-none">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Сводка услуг</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <StatRow label="Всего" value={String(stats.total)} />
              <StatRow label="Включено" value={String(stats.enabledCount)} />
              <StatRow label="Обязательных" value={String(stats.requiredCount)} />
              <StatRow label="За участника" value={String(stats.perParticipantCount)} />
              <StatRow label="За номер" value={String(stats.perPerformanceCount)} />
            </CardContent>
          </Card>

          {warnings.length > 0 ? (
            <Card className="shadow-none">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
                  Предупреждения
                  <Badge variant="warning" size="sm">
                    {warnings.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="max-h-64 space-y-2 overflow-y-auto">
                {warnings.slice(0, 12).map((warning) => (
                  <button
                    key={warning.id}
                    type="button"
                    className="w-full rounded-md border border-warning/35 bg-warning-surface/40 px-2.5 py-2 text-left text-warning-foreground text-xs transition-colors hover:bg-warning-surface/60"
                    onClick={() => {
                      if (warning.sectionId) onNavigateSection(warning.sectionId);
                    }}
                  >
                    {warning.message}
                  </button>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <AdditionalServiceFormDialog
        open={formOpen}
        mode={formMode}
        initialValues={formInitial}
        formats={competition.participationFormats}
        submitting={submitting}
        onOpenChange={setFormOpen}
        onSubmit={handleSubmit}
      />

      <Dialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Удалить доп. услугу?</DialogTitle>
            <DialogDescription>
              {deleteTarget
                ? `«${deleteTarget.name}» будет удалена. Это действие нельзя отменить.`
                : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeService.isPending}
              onClick={() => void handleDelete()}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }): React.JSX.Element {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
