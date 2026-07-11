import { AlertTriangle, Plus, Search, ShieldCheck } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import type {
  AdmissionRuleDraft,
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  admissionRuleKey,
  buildAdmissionCoverageWarnings,
  buildAdmissionLookupMaps,
  buildAdmissionRulesStats,
  draftFromRule,
  emptyAdmissionFilters,
  emptyAdmissionRuleDraft,
  filterAdmissionRules,
  planBulkAdmissionRules,
  resolveAdmissionRuleLabels,
  sortAdmissionRules,
  useAddAdmissionRuleMutation,
  useBulkAddAdmissionRulesMutation,
  useRemoveAdmissionRuleMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _AdmissionRule,
  AddAdmissionRule,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
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
  Input,
  PageSection,
  Select,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { AdmissionRuleCard } from "./admission-rule-card";
import { AdmissionRulesSkeleton } from "./admission-rules-skeleton";
import { EditAdmissionRuleDialog } from "./edit-admission-rule-dialog";
import { RuleBuilderDialog } from "./rule-builder-dialog";

const FILTER_ALL = "__all__";

interface AdmissionRulesSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function AdmissionRulesSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: AdmissionRulesSectionProps): React.JSX.Element {
  const isConfigurable = competition.status === "DRAFT" || competition.status === "CONFIGURED";
  const isReadOnly = !isConfigurable;

  const addRule = useAddAdmissionRuleMutation();
  const removeRule = useRemoveAdmissionRuleMutation();
  const bulkAdd = useBulkAddAdmissionRulesMutation();

  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [filters, setFilters] = useState(emptyAdmissionFilters());
  const [builderOpen, setBuilderOpen] = useState(false);
  const [builderDraft, setBuilderDraft] = useState<AdmissionRuleDraft>(emptyAdmissionRuleDraft());
  const [editTarget, setEditTarget] = useState<_AdmissionRule | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<_AdmissionRule | null>(null);
  const [sessionCreated, setSessionCreated] = useState(0);

  const maps = useMemo(() => buildAdmissionLookupMaps(competition), [competition]);
  const warnings = useMemo(() => buildAdmissionCoverageWarnings(competition), [competition]);
  const stats = useMemo(() => buildAdmissionRulesStats(competition), [competition]);

  const visibleRules = useMemo(() => {
    const filtered = filterAdmissionRules(
      competition.admissionRules,
      filters,
      deferredSearch,
      maps,
    );
    return sortAdmissionRules(filtered, maps);
  }, [competition.admissionRules, filters, deferredSearch, maps]);

  const prerequisitesMissing =
    competition.categories.length === 0 ||
    competition.disciplines.length === 0 ||
    competition.ageCategories.length === 0 ||
    competition.participantGroups.length === 0 ||
    !competition.participationFormats.some((item) => item.enabled);

  if (isLoading) {
    return <AdmissionRulesSkeleton />;
  }

  const apiErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof ApiError) {
      return error.problem?.detail ?? fallback;
    }
    return fallback;
  };

  const openBuilder = (draft?: AdmissionRuleDraft): void => {
    setBuilderDraft(draft ?? emptyAdmissionRuleDraft());
    setBuilderOpen(true);
  };

  const handleBulkCreate = async (draft: AdmissionRuleDraft): Promise<void> => {
    const plan = planBulkAdmissionRules(draft, maps.existingKeys);
    if (plan.toCreate.length === 0) return;

    onAutosaveStateChange("saving");
    try {
      const result = await bulkAdd.mutateAsync({
        competitionId: competition.id,
        payloads: plan.toCreate,
        skippedExisting: plan.skippedExisting,
      });
      setSessionCreated((count) => count + result.created);
      toast.success(
        result.skipped > 0
          ? `${result.created} создано · ${result.skipped} пропущено`
          : `${result.created} правил создано`,
      );
      setBuilderOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось создать правила допуска"));
    }
  };

  const handleEditSave = async (
    previous: AddAdmissionRule,
    next: AddAdmissionRule,
  ): Promise<void> => {
    if (admissionRuleKey(previous) === admissionRuleKey(next)) {
      setEditTarget(null);
      return;
    }

    onAutosaveStateChange("saving");
    try {
      await removeRule.mutateAsync({ competitionId: competition.id, payload: previous });
      try {
        await addRule.mutateAsync({ competitionId: competition.id, payload: next });
      } catch (error) {
        // Best-effort restore if the new combination is invalid.
        try {
          await addRule.mutateAsync({ competitionId: competition.id, payload: previous });
        } catch {
          // ignore restore failure; surface original error
        }
        throw error;
      }
      toast.success("Правило допуска обновлено");
      setEditTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось обновить правило допуска"));
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) return;
    onAutosaveStateChange("saving");
    try {
      await removeRule.mutateAsync({
        competitionId: competition.id,
        payload: {
          categoryId: deleteTarget.categoryId,
          disciplineId: deleteTarget.disciplineId,
          ageCategoryId: deleteTarget.ageCategoryId,
          participantGroupId: deleteTarget.participantGroupId,
          participationFormatId: deleteTarget.participationFormatId,
        },
      });
      toast.success("Правило допуска удалено");
      setDeleteTarget(null);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось удалить правило допуска"));
    }
  };

  const filterSelect = (
    label: string,
    value: string | null,
    options: Array<{ value: string; label: string }>,
    onChange: (next: string | null) => void,
  ): React.JSX.Element => (
    <Select
      label={label}
      value={value ?? FILTER_ALL}
      onValueChange={(next) => onChange(next === FILTER_ALL ? null : next)}
      options={[{ value: FILTER_ALL, label: "Все" }, ...options]}
      size="sm"
      containerClassName="min-w-0"
    />
  );

  const hasRules = competition.admissionRules.length > 0;
  const deleteLabels = deleteTarget ? resolveAdmissionRuleLabels(deleteTarget, maps) : null;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Раздел только для просмотра">
              Правила допуска можно изменять только в статусах «Черновик» и «Настроен».
            </Alert>
          ) : null}

          {prerequisitesMissing && !isReadOnly ? (
            <Alert variant="warning" title="Сначала заполните таксономию">
              Для конструктора нужны номинации, дисциплины, возрастные категории, группы участников
              и хотя бы один включённый формат участия.
            </Alert>
          ) : null}

          <PageSection
            title="Правила допуска"
            description="Разрешённые комбинации номинация → дисциплина → возраст → группа → формат. Основа цен, заявок и публикации."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-base">Комбинации</CardTitle>
                  {!isReadOnly && !prerequisitesMissing ? (
                    <Button type="button" size="sm" onClick={() => openBuilder()}>
                      <Plus className="size-3.5" aria-hidden="true" />
                      Конструктор правил
                    </Button>
                  ) : null}
                </div>

                {hasRules ? (
                  <div className="space-y-3">
                    <Input
                      label="Поиск"
                      placeholder="Номинация, дисциплина, возраст, группа, формат"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      leadingIcon={<Search aria-hidden="true" />}
                    />
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                      {filterSelect(
                        "Номинация",
                        filters.categoryId,
                        competition.categories.map((item) => ({
                          value: item.id,
                          label: item.name,
                        })),
                        (categoryId) =>
                          setFilters((current) => ({
                            ...current,
                            categoryId,
                            disciplineId: null,
                          })),
                      )}
                      {filterSelect(
                        "Дисциплина",
                        filters.disciplineId,
                        competition.disciplines
                          .filter(
                            (item) => !filters.categoryId || item.categoryId === filters.categoryId,
                          )
                          .map((item) => ({ value: item.id, label: item.name })),
                        (disciplineId) => setFilters((current) => ({ ...current, disciplineId })),
                      )}
                      {filterSelect(
                        "Возраст",
                        filters.ageCategoryId,
                        competition.ageCategories
                          .filter(
                            (item) => !filters.categoryId || item.categoryId === filters.categoryId,
                          )
                          .map((item) => ({ value: item.id, label: item.name })),
                        (ageCategoryId) => setFilters((current) => ({ ...current, ageCategoryId })),
                      )}
                      {filterSelect(
                        "Группа",
                        filters.participantGroupId,
                        competition.participantGroups
                          .filter(
                            (item) => !filters.categoryId || item.categoryId === filters.categoryId,
                          )
                          .map((item) => ({ value: item.id, label: item.name })),
                        (participantGroupId) =>
                          setFilters((current) => ({ ...current, participantGroupId })),
                      )}
                      {filterSelect(
                        "Формат",
                        filters.participationFormatId,
                        competition.participationFormats.map((item) => ({
                          value: item.id,
                          label: item.name,
                        })),
                        (participationFormatId) =>
                          setFilters((current) => ({ ...current, participationFormatId })),
                      )}
                    </div>
                  </div>
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {!hasRules ? (
                  <EmptyState
                    icon={<ShieldCheck />}
                    title="Правила допуска не созданы"
                    description="Соберите разрешённые комбинации в конструкторе — массово, без ручного перебора."
                    action={
                      !isReadOnly && !prerequisitesMissing ? (
                        <Button type="button" onClick={() => openBuilder()}>
                          Открыть конструктор
                        </Button>
                      ) : undefined
                    }
                  />
                ) : visibleRules.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поиск или фильтры." />
                ) : (
                  <ul
                    className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
                    aria-label="Правила допуска"
                  >
                    {visibleRules.map((rule) => (
                      <AdmissionRuleCard
                        key={admissionRuleKey(rule)}
                        rule={rule}
                        labels={resolveAdmissionRuleLabels(rule, maps)}
                        readOnly={isReadOnly}
                        onEdit={setEditTarget}
                        onDuplicate={(item) => openBuilder(draftFromRule(item))}
                        onDelete={setDeleteTarget}
                      />
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
              <CardTitle className="text-base">Статистика</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <StatRow label="Правил" value={String(stats.totalRules)} />
              <StatRow label="Создано за сессию" value={String(sessionCreated)} />
              <StatRow label="Покрытие дисциплин" value={`${stats.disciplineCoveragePercent}%`} />
              <StatRow
                label="Номинации с правилами"
                value={`${stats.nominationsWithRules} / ${stats.nominationsTotal}`}
              />
              <StatRow
                label="Дисциплины с правилами"
                value={`${stats.disciplinesWithRules} / ${stats.disciplinesTotal}`}
              />
            </CardContent>
          </Card>

          {warnings.length > 0 ? (
            <Card className="shadow-none">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <AlertTriangle className="size-4 text-amber-600" aria-hidden="true" />
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
                    className="w-full rounded-md border border-amber-200/80 bg-amber-50/50 px-2.5 py-2 text-left text-amber-950 text-xs transition-colors hover:bg-amber-50"
                    onClick={() => {
                      if (warning.sectionId) onNavigateSection(warning.sectionId);
                    }}
                  >
                    {warning.message}
                  </button>
                ))}
                {warnings.length > 12 ? (
                  <p className="text-muted-foreground text-xs">И ещё {warnings.length - 12}…</p>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <RuleBuilderDialog
        open={builderOpen}
        competition={competition}
        initialDraft={builderDraft}
        submitting={bulkAdd.isPending}
        onOpenChange={setBuilderOpen}
        onCreate={handleBulkCreate}
      />

      <EditAdmissionRuleDialog
        open={editTarget != null}
        competition={competition}
        rule={editTarget}
        submitting={addRule.isPending || removeRule.isPending}
        onOpenChange={(open) => {
          if (!open) setEditTarget(null);
        }}
        onSave={handleEditSave}
      />

      <Dialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить правило допуска?</DialogTitle>
            <DialogDescription>
              {deleteLabels
                ? `${deleteLabels.categoryName} → ${deleteLabels.disciplineName} → ${deleteLabels.ageCategoryName} → ${deleteLabels.participantGroupName} → ${deleteLabels.participationFormatName}`
                : "Комбинация будет удалена. Цены, завязанные на неё, могут заблокировать удаление."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeRule.isPending}
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
