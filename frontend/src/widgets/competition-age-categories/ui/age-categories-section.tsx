import { Check, ChevronDown, Copy, GripVertical, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  useAddAgeCategoryMutation,
  useRemoveAgeCategoryMutation,
  useReorderAgeCategoriesMutation,
  useUpdateAgeCategoryMutation,
} from "@/features/competitions";
import type { AgeCategoryKind, MixedAgeMethod } from "@/features/competitions/lib/age-categories";
import {
  AGE_CATEGORY_TYPE_LABELS,
  buildAgeCategoryReorderUpdates,
  buildAgeCategoryTree,
  createAgeCategoryPayload,
  duplicateAgeCategoryDraft,
  filterAgeCategoryTree,
  formatAgeRange,
  formatAgeRangeLabel,
  MIXED_AGE_METHOD_LABELS,
  moveIdBefore,
  nextAgeCategorySortOrder,
  updateAgeCategoryPayload,
} from "@/features/competitions/lib/age-categories";
import { ApiError } from "@/shared/api";
import type { _AgeCategory, CompetitionDetail } from "@/shared/api/generated/model-competitions";
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
import { AgeCategoriesSkeleton } from "./age-categories-skeleton";
import { AgeCategoryFormDialog, type AgeCategoryFormValues } from "./age-category-form-dialog";

interface AgeCategoriesSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function AgeCategoriesSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: AgeCategoriesSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "ARCHIVED";

  const addAgeCategory = useAddAgeCategoryMutation();
  const updateAgeCategory = useUpdateAgeCategoryMutation();
  const removeAgeCategory = useRemoveAgeCategoryMutation();
  const reorderAgeCategories = useReorderAgeCategoriesMutation();

  const [search, setSearch] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [formNominationName, setFormNominationName] = useState("");
  const [editingItem, setEditingItem] = useState<_AgeCategory | null>(null);
  const [formInitial, setFormInitial] = useState<AgeCategoryFormValues>({
    categoryId: "",
    name: "",
    minAge: 0,
    maxAge: 0,
    type: "STANDARD",
    mixedCalculationMethod: null,
  });
  const [deleteTarget, setDeleteTarget] = useState<_AgeCategory | null>(null);
  const [draggedItem, setDraggedItem] = useState<{
    id: string;
    categoryId: string;
  } | null>(null);

  const tree = useMemo(
    () => buildAgeCategoryTree(competition.categories, competition.ageCategories),
    [competition.categories, competition.ageCategories],
  );
  const filteredTree = useMemo(() => filterAgeCategoryTree(tree, search), [tree, search]);

  if (isLoading) {
    return <AgeCategoriesSkeleton />;
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
      minAge: 0,
      maxAge: 0,
      type: "STANDARD",
      mixedCalculationMethod: null,
    });
    setFormOpen(true);
  };

  const openEdit = (item: _AgeCategory, nominationName: string): void => {
    setFormMode("edit");
    setEditingItem(item);
    setFormNominationName(nominationName);
    setFormInitial({
      categoryId: item.categoryId,
      name: item.name,
      minAge: item.minAge,
      maxAge: item.maxAge,
      type: (item.type as AgeCategoryKind) || "STANDARD",
      mixedCalculationMethod: (item.mixedCalculationMethod as MixedAgeMethod | null) ?? null,
    });
    setFormOpen(true);
  };

  const openDuplicate = (item: _AgeCategory, nominationName: string): void => {
    const draft = duplicateAgeCategoryDraft(item);
    setFormMode("create");
    setEditingItem(null);
    setFormNominationName(nominationName);
    setFormInitial(draft);
    setFormOpen(true);
  };

  const handleSubmit = async (values: AgeCategoryFormValues): Promise<void> => {
    onAutosaveStateChange("saving");
    try {
      if (formMode === "create") {
        await addAgeCategory.mutateAsync({
          competitionId: competition.id,
          payload: createAgeCategoryPayload({
            ...values,
            sortOrder: nextAgeCategorySortOrder(competition.ageCategories, values.categoryId),
          }),
        });
        toast.success("Возрастная категория добавлена");
      } else if (editingItem) {
        await updateAgeCategory.mutateAsync({
          competitionId: competition.id,
          ageCategoryId: editingItem.id,
          payload: updateAgeCategoryPayload({
            name: values.name,
            minAge: values.minAge,
            maxAge: values.maxAge,
            type: values.type,
            mixedCalculationMethod: values.mixedCalculationMethod,
          }),
        });
        toast.success("Возрастная категория обновлена");
      }
      setFormOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось сохранить возрастную категорию"));
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      await removeAgeCategory.mutateAsync({
        competitionId: competition.id,
        ageCategoryId: deleteTarget.id,
      });
      toast.success("Возрастная категория удалена");
      setDeleteTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось удалить возрастную категорию"));
    }
  };

  const handleReorder = async (categoryId: string, fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || fromId === toId) return;
    const scopedItems = competition.ageCategories.filter((item) => item.categoryId === categoryId);
    const orderedIds = scopedItems
      .slice()
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .map((item) => item.id);
    const reordered = moveIdBefore(orderedIds, fromId, toId);
    const updates = buildAgeCategoryReorderUpdates(reordered, scopedItems);
    if (updates.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      await reorderAgeCategories.mutateAsync({ competitionId: competition.id, updates });
      onAutosaveStateChange("saved");
      toast.success("Порядок возрастных категорий обновлён");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось изменить порядок"));
    }
  };

  const hasNoNominations = competition.categories.length === 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Возрастные категории доступны только для просмотра.
            </Alert>
          ) : null}

          <PageSection
            title="Возрастные категории"
            description="Возрастные диапазоны для допуска участников и формирования цен, сгруппированные по номинациям."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <CardTitle className="text-base">Возрастные категории по номинациям</CardTitle>

                {!hasNoNominations ? (
                  <Input
                    label="Поиск"
                    placeholder="Название номинации или категории"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {hasNoNominations ? (
                  <EmptyState
                    title="Сначала создайте номинации"
                    description="Возрастные категории привязаны к номинациям. Создайте хотя бы одну номинацию."
                    action={
                      !isReadOnly ? (
                        <Button type="button" onClick={() => onNavigateSection("categories")}>
                          Перейти к номинациям
                        </Button>
                      ) : undefined
                    }
                  />
                ) : filteredTree.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поисковый запрос." />
                ) : (
                  <ul className="space-y-3" aria-label="Возрастные категории по номинациям">
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
                              {node.ageCategories.length}{" "}
                              {pluralAgeCategories(node.ageCategories.length)}
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
                              {node.ageCategories.length > 0 ? (
                                <ul
                                  className="space-y-2"
                                  aria-label={`Возрастные категории номинации ${node.nomination.name}`}
                                >
                                  {node.ageCategories.map((item) => (
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
                                        "flex items-center gap-2 rounded-md px-2 py-2 transition-colors hover:bg-muted/50",
                                        draggedItem?.id === item.id && "opacity-50",
                                      )}
                                    >
                                      {!isReadOnly && search.length === 0 ? (
                                        <span
                                          className="cursor-grab text-muted-foreground active:cursor-grabbing"
                                          aria-hidden="true"
                                          title="Перетащите для изменения порядка"
                                        >
                                          <GripVertical className="size-3.5" />
                                        </span>
                                      ) : null}

                                      <div className="min-w-0 flex-1">
                                        <p className="font-medium text-sm">{item.name}</p>
                                      </div>

                                      <Badge variant="outline" size="sm">
                                        {formatAgeRangeLabel(item.minAge, item.maxAge)}
                                      </Badge>

                                      <Badge variant="secondary" size="sm">
                                        {
                                          AGE_CATEGORY_TYPE_LABELS[
                                            (item.type as AgeCategoryKind) || "STANDARD"
                                          ]
                                        }
                                      </Badge>

                                      {item.type === "MIXED" &&
                                      item.mixedCalculationMethod != null ? (
                                        <Badge variant="outline" size="sm">
                                          {
                                            MIXED_AGE_METHOD_LABELS[
                                              item.mixedCalculationMethod as MixedAgeMethod
                                            ]
                                          }
                                        </Badge>
                                      ) : null}

                                      {!isReadOnly ? (
                                        <div className="flex gap-1">
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Редактировать возрастную категорию"
                                            icon={<Pencil className="size-3" aria-hidden="true" />}
                                            onClick={() => openEdit(item, node.nomination.name)}
                                          />
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Дублировать возрастную категорию"
                                            icon={<Copy className="size-3" aria-hidden="true" />}
                                            onClick={() =>
                                              openDuplicate(item, node.nomination.name)
                                            }
                                          />
                                          <IconButton
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            aria-label="Удалить возрастную категорию"
                                            icon={<Trash2 className="size-3" aria-hidden="true" />}
                                            onClick={() => setDeleteTarget(item)}
                                          />
                                        </div>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="py-2 text-center text-muted-foreground text-sm">
                                  В этой номинации пока нет возрастных категорий.
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
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Сводка</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {tree.length === 0 ? (
                <p className="text-muted-foreground">Нет номинаций.</p>
              ) : tree.every((node) => node.ageCategories.length === 0) ? (
                <p className="text-muted-foreground">Нет возрастных категорий.</p>
              ) : (
                <>
                  {tree
                    .filter((node) => node.ageCategories.length > 0)
                    .map((node) => (
                      <div key={node.nomination.id}>
                        <p className="font-medium text-muted-foreground mb-1">
                          {node.nomination.name}
                        </p>
                        <ul className="space-y-1">
                          {node.ageCategories.map((item) => (
                            <li
                              key={item.id}
                              className="flex items-center gap-2 text-muted-foreground"
                            >
                              <Check
                                className="size-3.5 shrink-0 text-green-600"
                                aria-hidden="true"
                              />
                              <span>{formatAgeRange(item.minAge, item.maxAge)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  <p className="pt-1 font-medium text-muted-foreground">
                    Всего: {competition.ageCategories.length}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <AgeCategoryFormDialog
        open={formOpen}
        mode={formMode}
        nominationName={formNominationName}
        initialValues={formInitial}
        submitting={addAgeCategory.isPending || updateAgeCategory.isPending}
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
            <DialogTitle>Удалить возрастную категорию?</DialogTitle>
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
              loading={removeAgeCategory.isPending}
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

function pluralAgeCategories(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "категория";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "категории";
  return "категорий";
}
