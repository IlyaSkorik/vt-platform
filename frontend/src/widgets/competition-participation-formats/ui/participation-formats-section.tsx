import {
  Check,
  ClipboardCheck,
  Copy,
  GripVertical,
  Pencil,
  Plus,
  Power,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  useAddParticipationFormatMutation,
  useRemoveParticipationFormatMutation,
  useReorderParticipationFormatsMutation,
  useUpdateParticipationFormatMutation,
} from "@/features/competitions";
import {
  buildParticipationFormatReorderUpdates,
  countEnabledFormats,
  createParticipationFormatPayload,
  duplicateParticipationFormatDraft,
  filterParticipationFormats,
  moveIdBefore,
  nextParticipationFormatSortOrder,
  sortParticipationFormats,
  updateParticipationFormatPayload,
} from "@/features/competitions/lib/participation-formats";
import { ApiError } from "@/shared/api";
import type {
  _ParticipationFormat,
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
import {
  ParticipationFormatFormDialog,
  type ParticipationFormatFormValues,
} from "./participation-format-form-dialog";
import { ParticipationFormatsSkeleton } from "./participation-formats-skeleton";

interface ParticipationFormatsSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function ParticipationFormatsSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: ParticipationFormatsSectionProps): React.JSX.Element {
  const isConfigurable = competition.status === "DRAFT" || competition.status === "CONFIGURED";
  const isReadOnly = !isConfigurable;

  const addFormat = useAddParticipationFormatMutation();
  const updateFormat = useUpdateParticipationFormatMutation();
  const removeFormat = useRemoveParticipationFormatMutation();
  const reorderFormats = useReorderParticipationFormatsMutation();

  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [editingItem, setEditingItem] = useState<_ParticipationFormat | null>(null);
  const [formInitial, setFormInitial] = useState<ParticipationFormatFormValues>({
    name: "",
    description: "",
    enabled: true,
  });
  const [deleteTarget, setDeleteTarget] = useState<_ParticipationFormat | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const sorted = useMemo(
    () => sortParticipationFormats(competition.participationFormats),
    [competition.participationFormats],
  );
  const filtered = useMemo(() => filterParticipationFormats(sorted, search), [sorted, search]);
  const enabledSorted = useMemo(() => sorted.filter((item) => item.enabled), [sorted]);
  const enabledCount = countEnabledFormats(sorted);

  if (isLoading) {
    return <ParticipationFormatsSkeleton />;
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
    setFormInitial({ name: "", description: "", enabled: true });
    setFormOpen(true);
  };

  const openEdit = (item: _ParticipationFormat): void => {
    setFormMode("edit");
    setEditingItem(item);
    setFormInitial({
      name: item.name,
      description: item.description ?? "",
      enabled: item.enabled,
    });
    setFormOpen(true);
  };

  const openDuplicate = (item: _ParticipationFormat): void => {
    const draft = duplicateParticipationFormatDraft(item);
    setFormMode("create");
    setEditingItem(null);
    setFormInitial(draft);
    setFormOpen(true);
  };

  const handleSubmit = async (values: ParticipationFormatFormValues): Promise<void> => {
    onAutosaveStateChange("saving");
    try {
      if (formMode === "create") {
        await addFormat.mutateAsync({
          competitionId: competition.id,
          payload: createParticipationFormatPayload({
            ...values,
            sortOrder: nextParticipationFormatSortOrder(competition.participationFormats),
          }),
        });
        toast.success("Формат участия добавлен");
      } else if (editingItem) {
        await updateFormat.mutateAsync({
          competitionId: competition.id,
          formatId: editingItem.id,
          payload: updateParticipationFormatPayload(values),
        });
        toast.success("Формат участия обновлён");
      }
      setFormOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось сохранить формат участия"));
    }
  };

  const handleToggleEnabled = async (item: _ParticipationFormat): Promise<void> => {
    if (isReadOnly) return;
    onAutosaveStateChange("saving");
    try {
      await updateFormat.mutateAsync({
        competitionId: competition.id,
        formatId: item.id,
        payload: { enabled: !item.enabled },
      });
      toast.success(item.enabled ? "Формат участия выключен" : "Формат участия включён");
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить статус формата"));
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      await removeFormat.mutateAsync({
        competitionId: competition.id,
        formatId: deleteTarget.id,
      });
      toast.success("Формат участия удалён");
      setDeleteTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось удалить формат участия"));
    }
  };

  const handleReorder = async (fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId || search.length > 0) return;
    const orderedIds = sorted.map((item) => item.id);
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildParticipationFormatReorderUpdates(reordered, sorted);
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderFormats.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок форматов участия обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок"));
    }
  };

  const hasNoFormats = competition.participationFormats.length === 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Раздел только для просмотра">
              Форматы участия можно изменять только в статусах «Черновик» и «Настроен».
            </Alert>
          ) : null}

          <PageSection
            title="Форматы участия"
            description="Способы участия в фестивале — для правил допуска, цен и заявок."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-base">Форматы</CardTitle>
                  {!isReadOnly && !hasNoFormats ? (
                    <Button type="button" size="sm" onClick={openCreate}>
                      <Plus className="size-3.5" aria-hidden="true" />
                      Создать формат
                    </Button>
                  ) : null}
                </div>

                {!hasNoFormats ? (
                  <Input
                    label="Поиск"
                    placeholder="Название или описание"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {hasNoFormats ? (
                  <EmptyState
                    icon={<ClipboardCheck />}
                    title="Форматы участия не созданы"
                    description="Добавьте способы участия — очно, онлайн или свои варианты."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={openCreate}>
                          Создать первый формат
                        </Button>
                      ) : undefined
                    }
                  />
                ) : filtered.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поисковый запрос." />
                ) : (
                  <ul className="grid gap-3 sm:grid-cols-2" aria-label="Форматы участия">
                    {filtered.map((item) => (
                      <li
                        key={item.id}
                        draggable={!isReadOnly && search.length === 0}
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = "move";
                          setDraggedId(item.id);
                        }}
                        onDragEnd={() => setDraggedId(null)}
                        onDragOver={(e) => {
                          if (draggedId && search.length === 0) {
                            e.preventDefault();
                          }
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
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
                                {item.enabled ? "Включён" : "Выключен"}
                              </Badge>
                            </div>
                            {item.description ? (
                              <p className="text-muted-foreground text-sm">{item.description}</p>
                            ) : (
                              <p className="text-muted-foreground text-sm italic">Без описания</p>
                            )}
                          </div>
                        </div>

                        {!isReadOnly ? (
                          <div className="mt-3 flex items-center gap-1">
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label="Редактировать формат участия"
                              icon={<Pencil className="size-3" aria-hidden="true" />}
                              onClick={() => openEdit(item)}
                            />
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label={
                                item.enabled
                                  ? "Выключить формат участия"
                                  : "Включить формат участия"
                              }
                              icon={<Power className="size-3" aria-hidden="true" />}
                              onClick={() => void handleToggleEnabled(item)}
                            />
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label="Дублировать формат участия"
                              icon={<Copy className="size-3" aria-hidden="true" />}
                              onClick={() => openDuplicate(item)}
                            />
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label="Удалить формат участия"
                              icon={<Trash2 className="size-3" aria-hidden="true" />}
                              onClick={() => setDeleteTarget(item)}
                            />
                          </div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </PageSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <Card className="shadow-none">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Форматы участия</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {enabledSorted.length === 0 ? (
                <p className="text-muted-foreground">Нет включённых форматов.</p>
              ) : (
                <ul className="space-y-1">
                  {enabledSorted.map((item) => (
                    <li key={item.id} className="flex items-center gap-2 text-muted-foreground">
                      <Check className="size-3.5 shrink-0 text-green-600" aria-hidden="true" />
                      <span>{item.name}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="pt-1 font-medium text-muted-foreground">
                Всего включено: {enabledCount}
              </p>
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <ParticipationFormatFormDialog
        open={formOpen}
        mode={formMode}
        initialValues={formInitial}
        submitting={addFormat.isPending || updateFormat.isPending}
        onOpenChange={setFormOpen}
        onSubmit={handleSubmit}
      />

      <Dialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить формат участия?</DialogTitle>
            <DialogDescription>
              «{deleteTarget?.name}» будет удалён из фестиваля. Это может повлиять на правила
              допуска и цены.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeFormat.isPending}
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
