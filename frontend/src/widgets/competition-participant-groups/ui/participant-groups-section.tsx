import {
  Check,
  ChevronDown,
  Copy,
  GripVertical,
  Pencil,
  Plus,
  Search,
  Trash2,
  Users,
} from "lucide-react";
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
  buildParticipantGroupTree,
  createParticipantGroupPayload,
  duplicateParticipantGroupDraft,
  filterParticipantGroupTree,
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

function pluralGroups(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "группа";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "группы";
  return "групп";
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
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(competition.categories.map((category) => category.id)),
  );
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [formNominationName, setFormNominationName] = useState("");
  const [editingItem, setEditingItem] = useState<_ParticipantGroup | null>(null);
  const [formInitial, setFormInitial] = useState<ParticipantGroupFormValues>({
    categoryId: "",
    name: "",
    minCount: 1,
    maxCount: 1,
    description: "",
    openEnded: false,
  });
  const [deleteTarget, setDeleteTarget] = useState<_ParticipantGroup | null>(null);
  const [draggedItem, setDraggedItem] = useState<{
    id: string;
    categoryId: string;
  } | null>(null);

  const tree = useMemo(
    () => buildParticipantGroupTree(competition.categories, competition.participantGroups),
    [competition.categories, competition.participantGroups],
  );
  const filteredTree = useMemo(() => filterParticipantGroupTree(tree, search), [tree, search]);
  const nominationOptions = useMemo(
    () =>
      competition.categories.map((category) => ({
        value: category.id,
        label: category.name,
      })),
    [competition.categories],
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

  const toggleExpanded = (categoryId: string): void => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const openCreate = (categoryId: string, nominationName: string): void => {
    setFormMode("create");
    setEditingItem(null);
    setFormNominationName(nominationName);
    setFormInitial({
      categoryId,
      name: "",
      minCount: 1,
      maxCount: 1,
      description: "",
      openEnded: false,
    });
    setFormOpen(true);
  };

  const openCreateFirst = (): void => {
    const first = competition.categories[0];
    if (!first) return;
    openCreate(first.id, first.name);
  };

  const openEdit = (item: _ParticipantGroup, nominationName: string): void => {
    setFormMode("edit");
    setEditingItem(item);
    setFormNominationName(nominationName);
    setFormInitial({
      categoryId: item.categoryId,
      name: item.name,
      minCount: item.minCount,
      maxCount: item.maxCount,
      description: item.description ?? "",
      openEnded: item.maxCount == null,
    });
    setFormOpen(true);
  };

  const openDuplicate = (item: _ParticipantGroup, nominationName: string): void => {
    const draft = duplicateParticipantGroupDraft(item);
    setFormMode("create");
    setEditingItem(null);
    setFormNominationName(nominationName);
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
            sortOrder: nextParticipantGroupSortOrder(
              competition.participantGroups,
              values.categoryId,
            ),
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

  const handleReorder = async (categoryId: string, fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId) return;
    const scopedItems = competition.participantGroups.filter(
      (item) => item.categoryId === categoryId,
    );
    const orderedIds = scopedItems
      .slice()
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .map((item) => item.id);
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildParticipantGroupReorderUpdates(reordered, scopedItems);
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

  const hasNoNominations = competition.categories.length === 0;
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
                  <CardTitle className="text-base">Группы по номинациям</CardTitle>
                  {!isReadOnly && !hasNoNominations && !hasNoGroups ? (
                    <Button type="button" size="sm" onClick={openCreateFirst}>
                      <Plus className="size-3.5" aria-hidden="true" />
                      Создать группу
                    </Button>
                  ) : null}
                </div>

                {!hasNoNominations && !hasNoGroups ? (
                  <Input
                    label="Поиск"
                    placeholder="Название номинации или группы"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {hasNoNominations ? (
                  <EmptyState
                    icon={<Users />}
                    title="Сначала создайте номинации"
                    description="Группы участников привязаны к номинациям. Создайте хотя бы одну номинацию."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={() => onNavigateSection("categories")}>
                          Перейти к номинациям
                        </Button>
                      ) : undefined
                    }
                  />
                ) : hasNoGroups ? (
                  <EmptyState
                    icon={<Users />}
                    title="Группы участников не созданы"
                    description="Добавьте типы состава — Solo, Duet, Ensemble или свои варианты."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={openCreateFirst}>
                          Создать первую группу
                        </Button>
                      ) : undefined
                    }
                  />
                ) : filteredTree.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поисковый запрос." />
                ) : (
                  <ul className="space-y-3" aria-label="Группы участников по номинациям">
                    {filteredTree.map((node) => {
                      const isExpanded = expandedIds.has(node.nomination.id);
                      return (
                        <li
                          key={node.nomination.id}
                          className="rounded-lg border border-border bg-background transition-colors"
                        >
                          <div className="flex items-center gap-2 px-3 py-3">
                            <button
                              type="button"
                              className="shrink-0 text-muted-foreground transition-transform"
                              aria-expanded={isExpanded}
                              aria-label={
                                isExpanded ? "Свернуть номинацию" : "Развернуть номинацию"
                              }
                              onClick={() => toggleExpanded(node.nomination.id)}
                            >
                              <ChevronDown
                                className={cn(
                                  "size-4 transition-transform duration-200",
                                  isExpanded ? "rotate-0" : "-rotate-90",
                                )}
                              />
                            </button>

                            <div className="min-w-0 flex-1">
                              <button
                                type="button"
                                className="cursor-default bg-transparent p-0 font-medium text-sm"
                                onClick={() => toggleExpanded(node.nomination.id)}
                              >
                                {node.nomination.name}
                              </button>
                            </div>

                            <Badge variant="secondary" size="sm">
                              {node.groups.length} {pluralGroups(node.groups.length)}
                            </Badge>

                            {!isReadOnly ? (
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => openCreate(node.nomination.id, node.nomination.name)}
                              >
                                <Plus className="size-3.5" aria-hidden="true" />
                                Добавить
                              </Button>
                            ) : null}
                          </div>

                          {isExpanded ? (
                            <div className="border-border border-t px-3 py-3">
                              {node.groups.length > 0 ? (
                                <ul
                                  className="grid gap-3 sm:grid-cols-2"
                                  aria-label={`Группы номинации ${node.nomination.name}`}
                                >
                                  {node.groups.map((item) => (
                                    <li
                                      key={item.id}
                                      draggable={!isReadOnly && search.length === 0}
                                      onDragStart={(e) => {
                                        e.stopPropagation();
                                        e.dataTransfer.effectAllowed = "move";
                                        setDraggedItem({
                                          id: item.id,
                                          categoryId: item.categoryId,
                                        });
                                      }}
                                      onDragEnd={() => setDraggedItem(null)}
                                      onDragOver={(e) => {
                                        if (
                                          draggedItem &&
                                          draggedItem.categoryId === node.nomination.id &&
                                          search.length === 0
                                        ) {
                                          e.preventDefault();
                                          e.stopPropagation();
                                        }
                                      }}
                                      onDrop={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        if (
                                          draggedItem &&
                                          draggedItem.categoryId === node.nomination.id
                                        ) {
                                          void handleReorder(
                                            node.nomination.id,
                                            draggedItem.id,
                                            item.id,
                                          );
                                        }
                                        setDraggedItem(null);
                                      }}
                                      className={cn(
                                        "rounded-lg border border-border bg-card p-3 transition-colors",
                                        draggedItem?.id === item.id && "opacity-50",
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
                                              {formatParticipantRangeLabel(
                                                item.minCount,
                                                item.maxCount,
                                              )}
                                            </Badge>
                                          </div>
                                          {item.description ? (
                                            <p className="text-muted-foreground text-sm">
                                              {item.description}
                                            </p>
                                          ) : (
                                            <p className="text-muted-foreground text-sm italic">
                                              Без описания
                                            </p>
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
                                            onClick={() => openEdit(item, node.nomination.name)}
                                          />
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Дублировать группу участников"
                                            icon={<Copy className="size-3" aria-hidden="true" />}
                                            onClick={() =>
                                              openDuplicate(item, node.nomination.name)
                                            }
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
                              ) : (
                                <p className="px-1 py-2 text-muted-foreground text-sm">
                                  В этой номинации ещё нет групп участников.
                                </p>
                              )}
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
              <CardTitle className="text-base">Группы участников</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {tree.length === 0 ? (
                <p className="text-muted-foreground">Нет номинаций.</p>
              ) : hasNoGroups ? (
                <p className="text-muted-foreground">Нет групп участников.</p>
              ) : (
                <>
                  {tree
                    .filter((node) => node.groups.length > 0)
                    .map((node) => (
                      <div key={node.nomination.id}>
                        <p className="mb-1 font-medium text-muted-foreground">
                          {node.nomination.name}
                        </p>
                        <ul className="space-y-1">
                          {node.groups.map((item) => (
                            <li
                              key={item.id}
                              className="flex items-center gap-2 text-muted-foreground"
                            >
                              <Check
                                className="size-3.5 shrink-0 text-green-600"
                                aria-hidden="true"
                              />
                              <span>
                                {item.name} ({formatParticipantRange(item.minCount, item.maxCount)})
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
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
        nominationName={formNominationName}
        nominationOptions={nominationOptions}
        allowNominationChange={competition.categories.length > 1}
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
