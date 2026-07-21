import { Check, Copy, GripVertical, Pencil, Plus, Search, Trash2, Users } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  useAddParticipantGroupMutation,
  useRemoveParticipantGroupMutation,
  useReorderParticipantGroupsMutation,
  useUpdateParticipantGroupMutation,
} from "@/features/competitions";
import {
  buildParticipantGroupReorderUpdates,
  createParticipantGroupPayload,
  duplicateParticipantGroupDraft,
  filterParticipantGroups,
  formatParticipantRange,
  formatParticipantRangeLabel,
  moveIdBefore,
  nextParticipantGroupSortOrder,
  updateParticipantGroupPayload,
} from "@/features/competitions/lib/participant-groups";
import { ApiError } from "@/shared/api";
import type {
  _ParticipantGroup,
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
  ParticipantGroupFormDialog,
  type ParticipantGroupFormValues,
} from "./participant-group-form-dialog";
import { ParticipantGroupsSkeleton } from "./participant-groups-skeleton";

interface ParticipantGroupsSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function ParticipantGroupsSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: ParticipantGroupsSectionProps): React.JSX.Element {
  const isConfigurable = competition.status === "DRAFT" || competition.status === "CONFIGURED";
  const isReadOnly = !isConfigurable;

  const addGroup = useAddParticipantGroupMutation();
  const updateGroup = useUpdateParticipantGroupMutation();
  const removeGroup = useRemoveParticipantGroupMutation();
  const reorderGroups = useReorderParticipantGroupsMutation();

  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [editingItem, setEditingItem] = useState<_ParticipantGroup | null>(null);
  const [formInitial, setFormInitial] = useState<ParticipantGroupFormValues>({
    name: "",
    minCount: 1,
    maxCount: 1,
    description: "",
    openEnded: false,
  });
  const [deleteTarget, setDeleteTarget] = useState<_ParticipantGroup | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const filtered = useMemo(
    () => filterParticipantGroups(competition.participantGroups, search),
    [competition.participantGroups, search],
  );

  if (isLoading) {
    return <ParticipantGroupsSkeleton />;
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
    setFormInitial({
      name: "",
      minCount: 1,
      maxCount: 1,
      description: "",
      openEnded: false,
    });
    setFormOpen(true);
  };

  const openEdit = (item: _ParticipantGroup): void => {
    setFormMode("edit");
    setEditingItem(item);
    setFormInitial({
      name: item.name,
      minCount: item.minCount,
      maxCount: item.maxCount,
      description: item.description ?? "",
      openEnded: item.maxCount == null,
    });
    setFormOpen(true);
  };

  const openDuplicate = (item: _ParticipantGroup): void => {
    const draft = duplicateParticipantGroupDraft(item);
    setFormMode("create");
    setEditingItem(null);
    setFormInitial({
      ...draft,
      openEnded: draft.maxCount == null,
    });
    setFormOpen(true);
  };

  const handleSubmit = async (values: ParticipantGroupFormValues): Promise<void> => {
    onAutosaveStateChange("saving");
    try {
      if (formMode === "create") {
        await addGroup.mutateAsync({
          competitionId: competition.id,
          payload: createParticipantGroupPayload({
            ...values,
            sortOrder: nextParticipantGroupSortOrder(competition.participantGroups),
          }),
        });
        toast.success("Группа участников добавлена");
      } else if (editingItem) {
        await updateGroup.mutateAsync({
          competitionId: competition.id,
          participantGroupId: editingItem.id,
          payload: updateParticipantGroupPayload({
            name: values.name,
            minCount: values.minCount,
            maxCount: values.maxCount,
            description: values.description,
          }),
        });
        toast.success("Группа участников обновлена");
      }
      setFormOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось сохранить группу участников"));
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      await removeGroup.mutateAsync({
        competitionId: competition.id,
        participantGroupId: deleteTarget.id,
      });
      toast.success("Группа участников удалена");
      setDeleteTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось удалить группу участников"));
    }
  };

  const handleReorder = async (fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId) return;
    const orderedIds = filterParticipantGroups(competition.participantGroups, "").map(
      (item) => item.id,
    );
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildParticipantGroupReorderUpdates(reordered, competition.participantGroups);
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderGroups.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок групп участников обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок"));
    }
  };

  const hasNoGroups = competition.participantGroups.length === 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Раздел только для просмотра">
              Группы участников можно изменять только в статусах «Черновик» и «Настроен».
            </Alert>
          ) : null}

          <PageSection
            title="Группы участников"
            description="Типы состава участников по численности — для правил допуска, цен, заявок и статистики."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-base">Группы участников</CardTitle>
                  {!isReadOnly && !hasNoGroups ? (
                    <Button type="button" size="sm" onClick={openCreate}>
                      <Plus className="size-3.5" aria-hidden="true" />
                      Добавить группу
                    </Button>
                  ) : null}
                </div>

                {!hasNoGroups ? (
                  <Input
                    label="Поиск"
                    placeholder="Название или описание группы"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {hasNoGroups ? (
                  <EmptyState
                    icon={<Users />}
                    title="Группы участников не созданы"
                    description="Добавьте типы состава — Solo, Duet, Ensemble или свои варианты."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={openCreate}>
                          Создать первую группу
                        </Button>
                      ) : undefined
                    }
                  />
                ) : filtered.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поисковый запрос." />
                ) : (
                  <ul className="grid gap-3 sm:grid-cols-2" aria-label="Группы участников">
                    {filtered.map((item) => (
                      <li
                        key={item.id}
                        draggable={!isReadOnly && search.length === 0}
                        onDragStart={(e) => {
                          e.stopPropagation();
                          e.dataTransfer.effectAllowed = "move";
                          setDraggedId(item.id);
                        }}
                        onDragEnd={() => setDraggedId(null)}
                        onDragOver={(e) => {
                          if (draggedId && search.length === 0) {
                            e.preventDefault();
                            e.stopPropagation();
                          }
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
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
                              <Badge variant="outline" size="sm">
                                {formatParticipantRangeLabel(item.minCount, item.maxCount)}
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
                              aria-label="Редактировать группу участников"
                              icon={<Pencil className="size-3" aria-hidden="true" />}
                              onClick={() => openEdit(item)}
                            />
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label="Дублировать группу участников"
                              icon={<Copy className="size-3" aria-hidden="true" />}
                              onClick={() => openDuplicate(item)}
                            />
                            <IconButton
                              type="button"
                              size="sm"
                              variant="ghost"
                              aria-label="Удалить группу участников"
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
              <CardTitle className="text-base">Группы участников</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {hasNoGroups ? (
                <p className="text-muted-foreground">Нет групп участников.</p>
              ) : (
                <>
                  <ul className="space-y-1">
                    {filterParticipantGroups(competition.participantGroups, "").map((item) => (
                      <li key={item.id} className="flex items-center gap-2 text-muted-foreground">
                        <Check className="size-3.5 shrink-0 text-success" aria-hidden="true" />
                        <span>
                          {item.name} ({formatParticipantRange(item.minCount, item.maxCount)})
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="pt-1 font-medium text-muted-foreground">
                    Всего: {competition.participantGroups.length}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <ParticipantGroupFormDialog
        open={formOpen}
        mode={formMode}
        initialValues={formInitial}
        submitting={addGroup.isPending || updateGroup.isPending}
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
            <DialogTitle>Удалить группу участников?</DialogTitle>
            <DialogDescription>
              «{deleteTarget?.name}» будет удалена из фестиваля. Это может повлиять на правила
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
              loading={removeGroup.isPending}
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
