import { ChevronDown, GripVertical, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  buildCategoryReorderUpdates,
  buildDisciplineReorderUpdates,
  buildTaxonomyTree,
  createCategoryPayload,
  createDisciplinePayload,
  filterTaxonomyTree,
  moveIdBefore,
  nextCategorySortOrder,
  nextDisciplineSortOrder,
  useAddCategoryMutation,
  useAddDisciplineMutation,
  useRemoveCategoryMutation,
  useRemoveDisciplineMutation,
  useReorderCategoriesMutation,
  useReorderDisciplinesMutation,
  useUpdateCategoryMutation,
  useUpdateDisciplineMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _Category,
  _Discipline,
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
  Textarea,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { CategoriesSkeleton } from "./categories-skeleton";
import { NominationRegistration } from "./nomination-registration";

interface CategoriesSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function CategoriesSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: CategoriesSectionProps): React.JSX.Element {
  const isConfigurable = competition.status === "DRAFT" || competition.status === "CONFIGURED";
  const isReadOnly = !isConfigurable;
  // Registration scheduling is a live control (available after publication), unlike
  // taxonomy editing; only an archived competition freezes it.
  const isArchived = competition.status === "ARCHIVED";

  const addCategory = useAddCategoryMutation();
  const updateCategory = useUpdateCategoryMutation();
  const removeCategory = useRemoveCategoryMutation();
  const reorderCategories = useReorderCategoriesMutation();
  const addDiscipline = useAddDisciplineMutation();
  const updateDiscipline = useUpdateDisciplineMutation();
  const removeDiscipline = useRemoveDisciplineMutation();
  const reorderDisciplines = useReorderDisciplinesMutation();

  const [search, setSearch] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [deleteTarget, setDeleteTarget] = useState<
    { type: "category"; item: _Category } | { type: "discipline"; item: _Discipline } | null
  >(null);
  const [draggedCategoryId, setDraggedCategoryId] = useState<string | null>(null);
  const [draggedDiscipline, setDraggedDiscipline] = useState<{
    id: string;
    categoryId: string;
  } | null>(null);

  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [editCategoryName, setEditCategoryName] = useState("");
  const [editingCategoryDescId, setEditingCategoryDescId] = useState<string | null>(null);
  const [editCategoryDesc, setEditCategoryDesc] = useState("");

  const [editingDisciplineId, setEditingDisciplineId] = useState<string | null>(null);
  const [editDisciplineName, setEditDisciplineName] = useState("");

  const [addingDisciplineCategoryId, setAddingDisciplineCategoryId] = useState<string | null>(null);
  const [newDisciplineName, setNewDisciplineName] = useState("");

  const addDisciplineInputRef = useRef<HTMLInputElement>(null);

  const tree = useMemo(
    () => buildTaxonomyTree(competition.categories, competition.disciplines),
    [competition.categories, competition.disciplines],
  );
  const filteredTree = useMemo(() => filterTaxonomyTree(tree, search), [tree, search]);

  if (isLoading) {
    return <CategoriesSkeleton />;
  }

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

  const apiErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof ApiError) {
      return error.problem?.detail ?? fallback;
    }
    return fallback;
  };

  const handleAddCategory = async (): Promise<void> => {
    onAutosaveStateChange("saving");
    try {
      const result = await addCategory.mutateAsync({
        competitionId: competition.id,
        payload: createCategoryPayload({
          name: "Новая номинация",
          sortOrder: nextCategorySortOrder(competition.categories),
        }),
      });
      const created = result.categories.find(
        (c) => !competition.categories.some((existing) => existing.id === c.id),
      );
      if (created) {
        setExpandedIds((prev) => new Set(prev).add(created.id));
        setEditingCategoryId(created.id);
        setEditCategoryName(created.name);
      }
      onAutosaveStateChange("saved");
      toast.success("Номинация добавлена");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось добавить номинацию"));
    }
  };

  const handleSaveCategoryName = async (categoryId: string): Promise<void> => {
    const trimmed = editCategoryName.trim();
    if (trimmed.length === 0) {
      setEditingCategoryId(null);
      return;
    }
    const existing = competition.categories.find((c) => c.id === categoryId);
    if (existing && existing.name === trimmed) {
      setEditingCategoryId(null);
      return;
    }
    onAutosaveStateChange("saving");
    try {
      await updateCategory.mutateAsync({
        competitionId: competition.id,
        categoryId,
        payload: { name: trimmed },
      });
      onAutosaveStateChange("saved");
      toast.success("Номинация переименована");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось переименовать номинацию"));
    }
    setEditingCategoryId(null);
  };

  const handleSaveCategoryDescription = async (categoryId: string): Promise<void> => {
    const trimmed = editCategoryDesc.trim();
    const existing = competition.categories.find((c) => c.id === categoryId);
    const current = existing?.description ?? "";
    if (trimmed === current) {
      setEditingCategoryDescId(null);
      return;
    }
    onAutosaveStateChange("saving");
    try {
      await updateCategory.mutateAsync({
        competitionId: competition.id,
        categoryId,
        payload: { description: trimmed.length > 0 ? trimmed : null },
      });
      onAutosaveStateChange("saved");
      toast.success("Описание обновлено");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось обновить описание"));
    }
    setEditingCategoryDescId(null);
  };

  const handleDeleteConfirm = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      if (deleteTarget.type === "category") {
        await removeCategory.mutateAsync({
          competitionId: competition.id,
          categoryId: deleteTarget.item.id,
        });
        toast.success("Номинация удалена");
      } else {
        await removeDiscipline.mutateAsync({
          competitionId: competition.id,
          disciplineId: deleteTarget.item.id,
        });
        toast.success("Дисциплина удалена");
      }
      onAutosaveStateChange("saved");
      setDeleteTarget(null);
    } catch (error) {
      onAutosaveStateChange("error");
      const fallback =
        deleteTarget.type === "category"
          ? "Не удалось удалить номинацию"
          : "Не удалось удалить дисциплину";
      toast.error(apiErrorMessage(error, fallback));
    }
  };

  const handleCategoryReorder = async (fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId) return;
    const orderedIds = tree.map((n) => n.category.id);
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildCategoryReorderUpdates(reordered, competition.categories);
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderCategories.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок номинаций обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок номинаций"));
    }
  };

  const handleDisciplineReorder = async (
    categoryId: string,
    fromId: string,
    toId: string,
  ): Promise<void> => {
    if (isReadOnly || fromId === toId) return;
    const node = tree.find((n) => n.category.id === categoryId);
    if (!node) return;
    const orderedIds = node.disciplines.map((d) => d.id);
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildDisciplineReorderUpdates(
      reordered,
      competition.disciplines.filter((d) => d.categoryId === categoryId),
    );
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderDisciplines.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок дисциплин обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок дисциплин"));
    }
  };

  const handleAddDiscipline = async (categoryId: string): Promise<void> => {
    const trimmed = newDisciplineName.trim();
    if (trimmed.length === 0) {
      setAddingDisciplineCategoryId(null);
      return;
    }
    onAutosaveStateChange("saving");
    try {
      await addDiscipline.mutateAsync({
        competitionId: competition.id,
        payload: createDisciplinePayload({
          categoryId,
          name: trimmed,
          sortOrder: nextDisciplineSortOrder(competition.disciplines, categoryId),
        }),
      });
      onAutosaveStateChange("saved");
      toast.success("Дисциплина добавлена");
      setNewDisciplineName("");
      setTimeout(() => addDisciplineInputRef.current?.focus(), 0);
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось добавить дисциплину"));
    }
  };

  const handleSaveDisciplineName = async (disciplineId: string): Promise<void> => {
    const trimmed = editDisciplineName.trim();
    if (trimmed.length === 0) {
      setEditingDisciplineId(null);
      return;
    }
    const existing = competition.disciplines.find((d) => d.id === disciplineId);
    if (existing && existing.name === trimmed) {
      setEditingDisciplineId(null);
      return;
    }
    onAutosaveStateChange("saving");
    try {
      await updateDiscipline.mutateAsync({
        competitionId: competition.id,
        disciplineId,
        payload: { name: trimmed },
      });
      onAutosaveStateChange("saved");
      toast.success("Дисциплина переименована");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось переименовать дисциплину"));
    }
    setEditingDisciplineId(null);
  };

  const deleteDialogTitle =
    deleteTarget?.type === "category" ? "Удалить номинацию?" : "Удалить дисциплину?";
  const deleteDialogDescription = deleteTarget
    ? deleteTarget.type === "category"
      ? `Номинация «${deleteTarget.item.name}» и все её дисциплины будут удалены из фестиваля.`
      : `Дисциплина «${deleteTarget.item.name}» будет удалена из фестиваля.`
    : "";

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Раздел только для просмотра">
              Номинации и дисциплины можно изменять только в статусах «Черновик» и «Настроен».
            </Alert>
          ) : null}

          <PageSection
            title="Номинации и дисциплины"
            description="Таксономия фестиваля: номинации объединяют дисциплины и формируют структуру программы."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <CardTitle className="text-base">Структура номинаций</CardTitle>
                  {!isReadOnly ? (
                    <Button
                      type="button"
                      onClick={() => void handleAddCategory()}
                      loading={addCategory.isPending}
                    >
                      <Plus className="size-4" aria-hidden="true" />
                      Добавить номинацию
                    </Button>
                  ) : null}
                </div>

                <Input
                  label="Поиск"
                  placeholder="Название номинации или дисциплины"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  leadingIcon={<Search aria-hidden="true" />}
                />
              </CardHeader>

              <CardContent className="space-y-3">
                {filteredTree.length === 0 ? (
                  <EmptyState
                    title={
                      competition.categories.length === 0
                        ? "Номинаций пока нет"
                        : "Ничего не найдено"
                    }
                    description={
                      competition.categories.length === 0
                        ? "Добавьте первую номинацию, чтобы начать формировать программу фестиваля."
                        : "Измените поисковый запрос."
                    }
                    action={
                      !isReadOnly && competition.categories.length === 0 ? (
                        <Button
                          type="button"
                          onClick={() => void handleAddCategory()}
                          loading={addCategory.isPending}
                        >
                          Добавить номинацию
                        </Button>
                      ) : undefined
                    }
                  />
                ) : (
                  <ul className="space-y-3" aria-label="Список номинаций фестиваля">
                    {filteredTree.map((node) => {
                      const isExpanded = expandedIds.has(node.category.id);
                      return (
                        <li
                          key={node.category.id}
                          draggable={!isReadOnly && search.length === 0}
                          onDragStart={(e) => {
                            e.dataTransfer.effectAllowed = "move";
                            setDraggedCategoryId(node.category.id);
                          }}
                          onDragEnd={() => setDraggedCategoryId(null)}
                          onDragOver={(e) => {
                            if (draggedCategoryId && !isReadOnly && search.length === 0) {
                              e.preventDefault();
                            }
                          }}
                          onDrop={(e) => {
                            e.preventDefault();
                            if (draggedCategoryId) {
                              void handleCategoryReorder(draggedCategoryId, node.category.id);
                            }
                            setDraggedCategoryId(null);
                          }}
                          className={cn(
                            "rounded-lg border border-border bg-background transition-colors",
                            draggedCategoryId === node.category.id && "opacity-50",
                          )}
                        >
                          <div className="flex items-start gap-2 px-3 py-3">
                            {!isReadOnly && search.length === 0 ? (
                              <span
                                className="mt-1 cursor-grab text-muted-foreground active:cursor-grabbing"
                                aria-hidden="true"
                                title="Перетащите для изменения порядка"
                              >
                                <GripVertical className="size-4" />
                              </span>
                            ) : null}

                            <button
                              type="button"
                              className="mt-1 shrink-0 text-muted-foreground transition-transform"
                              aria-expanded={isExpanded}
                              aria-label={
                                isExpanded ? "Свернуть номинацию" : "Развернуть номинацию"
                              }
                              onClick={() => toggleExpanded(node.category.id)}
                            >
                              <ChevronDown
                                className={cn(
                                  "size-4 transition-transform duration-200",
                                  isExpanded ? "rotate-0" : "-rotate-90",
                                )}
                              />
                            </button>

                            <div className="min-w-0 flex-1 space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                                {editingCategoryId === node.category.id ? (
                                  <Input
                                    className="h-7 max-w-xs text-sm"
                                    value={editCategoryName}
                                    onChange={(e) => setEditCategoryName(e.target.value)}
                                    onBlur={() => void handleSaveCategoryName(node.category.id)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter")
                                        void handleSaveCategoryName(node.category.id);
                                      if (e.key === "Escape") setEditingCategoryId(null);
                                    }}
                                    autoFocus
                                  />
                                ) : (
                                  <button
                                    type="button"
                                    className="cursor-default bg-transparent p-0 font-medium text-sm"
                                    onDoubleClick={() => {
                                      if (isReadOnly) return;
                                      setEditingCategoryId(node.category.id);
                                      setEditCategoryName(node.category.name);
                                    }}
                                  >
                                    {node.category.name}
                                  </button>
                                )}
                                <Badge variant="secondary" size="sm">
                                  {node.disciplines.length}{" "}
                                  {pluralDisciplines(node.disciplines.length)}
                                </Badge>
                              </div>

                              {editingCategoryDescId === node.category.id ? (
                                <Textarea
                                  className="max-w-md text-sm"
                                  rows={2}
                                  value={editCategoryDesc}
                                  onChange={(e) => setEditCategoryDesc(e.target.value)}
                                  onBlur={() =>
                                    void handleSaveCategoryDescription(node.category.id)
                                  }
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                      e.preventDefault();
                                      void handleSaveCategoryDescription(node.category.id);
                                    }
                                    if (e.key === "Escape") setEditingCategoryDescId(null);
                                  }}
                                  autoFocus
                                />
                              ) : isReadOnly ? (
                                <p className="text-muted-foreground text-sm">
                                  {node.category.description}
                                </p>
                              ) : (
                                <button
                                  type="button"
                                  className="cursor-pointer bg-transparent p-0 text-left text-muted-foreground text-sm"
                                  onDoubleClick={() => {
                                    setEditingCategoryDescId(node.category.id);
                                    setEditCategoryDesc(node.category.description ?? "");
                                  }}
                                >
                                  {node.category.description ||
                                    "Нажмите дважды, чтобы добавить описание"}
                                </button>
                              )}
                            </div>

                            {!isReadOnly ? (
                              <div className="flex gap-1">
                                <IconButton
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  aria-label="Редактировать название номинации"
                                  icon={<Pencil aria-hidden="true" />}
                                  onClick={() => {
                                    setEditingCategoryId(node.category.id);
                                    setEditCategoryName(node.category.name);
                                  }}
                                />
                                <IconButton
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  aria-label="Удалить номинацию"
                                  icon={<Trash2 aria-hidden="true" />}
                                  onClick={() =>
                                    setDeleteTarget({ type: "category", item: node.category })
                                  }
                                />
                              </div>
                            ) : null}
                          </div>

                          {isExpanded ? (
                            <div className="space-y-3 border-border border-t px-3 py-3">
                              <NominationRegistration
                                competitionId={competition.id}
                                category={node.category}
                                disabled={isArchived}
                              />
                              {node.disciplines.length > 0 ? (
                                <ul
                                  className="space-y-2"
                                  aria-label={`Дисциплины номинации ${node.category.name}`}
                                >
                                  {node.disciplines.map((discipline) => (
                                    <li
                                      key={discipline.id}
                                      draggable={!isReadOnly}
                                      onDragStart={(e) => {
                                        e.stopPropagation();
                                        e.dataTransfer.effectAllowed = "move";
                                        setDraggedDiscipline({
                                          id: discipline.id,
                                          categoryId: node.category.id,
                                        });
                                      }}
                                      onDragEnd={() => setDraggedDiscipline(null)}
                                      onDragOver={(e) => {
                                        if (
                                          draggedDiscipline &&
                                          draggedDiscipline.categoryId === node.category.id
                                        ) {
                                          e.preventDefault();
                                          e.stopPropagation();
                                        }
                                      }}
                                      onDrop={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        if (
                                          draggedDiscipline &&
                                          draggedDiscipline.categoryId === node.category.id
                                        ) {
                                          void handleDisciplineReorder(
                                            node.category.id,
                                            draggedDiscipline.id,
                                            discipline.id,
                                          );
                                        }
                                        setDraggedDiscipline(null);
                                      }}
                                      className={cn(
                                        "flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50",
                                        draggedDiscipline?.id === discipline.id && "opacity-50",
                                      )}
                                    >
                                      {!isReadOnly ? (
                                        <span
                                          className="cursor-grab text-muted-foreground active:cursor-grabbing"
                                          aria-hidden="true"
                                        >
                                          <GripVertical className="size-3.5" />
                                        </span>
                                      ) : null}

                                      {editingDisciplineId === discipline.id ? (
                                        <Input
                                          className="h-7 flex-1 text-sm"
                                          value={editDisciplineName}
                                          onChange={(e) => setEditDisciplineName(e.target.value)}
                                          onBlur={() =>
                                            void handleSaveDisciplineName(discipline.id)
                                          }
                                          onKeyDown={(e) => {
                                            if (e.key === "Enter")
                                              void handleSaveDisciplineName(discipline.id);
                                            if (e.key === "Escape") setEditingDisciplineId(null);
                                          }}
                                          autoFocus
                                        />
                                      ) : (
                                        <button
                                          type="button"
                                          className="min-w-0 flex-1 cursor-default truncate bg-transparent p-0 text-left text-sm"
                                          onDoubleClick={() => {
                                            if (isReadOnly) return;
                                            setEditingDisciplineId(discipline.id);
                                            setEditDisciplineName(discipline.name);
                                          }}
                                        >
                                          {discipline.name}
                                        </button>
                                      )}

                                      {!isReadOnly ? (
                                        <div className="flex gap-1">
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Редактировать дисциплину"
                                            icon={<Pencil className="size-3" aria-hidden="true" />}
                                            onClick={() => {
                                              setEditingDisciplineId(discipline.id);
                                              setEditDisciplineName(discipline.name);
                                            }}
                                          />
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Удалить дисциплину"
                                            icon={<Trash2 className="size-3" aria-hidden="true" />}
                                            onClick={() =>
                                              setDeleteTarget({
                                                type: "discipline",
                                                item: discipline,
                                              })
                                            }
                                          />
                                        </div>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="py-2 text-center text-muted-foreground text-sm">
                                  В этой номинации пока нет дисциплин.
                                </p>
                              )}

                              {!isReadOnly ? (
                                <div className="mt-3">
                                  {addingDisciplineCategoryId === node.category.id ? (
                                    <div className="flex items-center gap-2">
                                      <Input
                                        ref={addDisciplineInputRef}
                                        className="h-7 flex-1 text-sm"
                                        placeholder="Название дисциплины"
                                        value={newDisciplineName}
                                        onChange={(e) => setNewDisciplineName(e.target.value)}
                                        onKeyDown={(e) => {
                                          if (e.key === "Enter")
                                            void handleAddDiscipline(node.category.id);
                                          if (e.key === "Escape") {
                                            setAddingDisciplineCategoryId(null);
                                            setNewDisciplineName("");
                                          }
                                        }}
                                        autoFocus
                                      />
                                      <Button
                                        type="button"
                                        size="sm"
                                        onClick={() => void handleAddDiscipline(node.category.id)}
                                        loading={addDiscipline.isPending}
                                      >
                                        Добавить
                                      </Button>
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => {
                                          setAddingDisciplineCategoryId(null);
                                          setNewDisciplineName("");
                                        }}
                                      >
                                        Отмена
                                      </Button>
                                    </div>
                                  ) : (
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => {
                                        setAddingDisciplineCategoryId(node.category.id);
                                        setNewDisciplineName("");
                                      }}
                                    >
                                      <Plus className="size-3.5" aria-hidden="true" />
                                      Добавить дисциплину
                                    </Button>
                                  )}
                                </div>
                              ) : null}
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
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Как работать с номинациями</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-muted-foreground text-sm">
              <p>1. Создайте номинации — крупные направления фестиваля.</p>
              <p>2. Внутри каждой номинации добавьте дисциплины.</p>
              <p>3. Перетаскивайте элементы, чтобы задать порядок отображения.</p>
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <Dialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{deleteDialogTitle}</DialogTitle>
            <DialogDescription>{deleteDialogDescription}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeCategory.isPending || removeDiscipline.isPending}
              onClick={() => void handleDeleteConfirm()}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function pluralDisciplines(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "дисциплина";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "дисциплины";
  return "дисциплин";
}
