import { AlertTriangle, CircleDollarSign, Copy, Search } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type {
  AutosaveState,
  BulkPriceOperation,
  CompetitionSectionId,
  CopyPricingDimension,
  PricingRow,
  PublicationChecklist,
} from "@/features/competitions";
import {
  buildAdmissionLookupMaps,
  buildPricingRows,
  buildPricingStats,
  buildPricingWarnings,
  copyPlanToMutations,
  emptyPricingFilters,
  filterPricingRows,
  formatAmount,
  planBulkPricingMutations,
  planCopyPricing,
  useBulkPricingMutation,
  useUpsertPricingRuleMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  PageSection,
  Select,
  toast,
} from "@/shared/ui";
import { PerformanceDiscountCard } from "@/widgets/competition-settings";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { type BulkMode, PricingBulkDialog, PricingBulkToolbar } from "./pricing-bulk-dialog";
import { PricingCard } from "./pricing-card";
import { PricingCopyDialog } from "./pricing-copy-dialog";
import { PricingSkeleton } from "./pricing-skeleton";

const FILTER_ALL = "__all__";

interface PricingSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function PricingSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: PricingSectionProps): React.JSX.Element {
  const isConfigurable = competition.status === "DRAFT" || competition.status === "CONFIGURED";
  const isReadOnly = !isConfigurable;
  const upsertPrice = useUpsertPricingRuleMutation();
  const bulkPricing = useBulkPricingMutation();

  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [filters, setFilters] = useState(emptyPricingFilters());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkMode, setBulkMode] = useState<BulkMode | null>(null);
  const [copyOpen, setCopyOpen] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const maps = useMemo(() => buildAdmissionLookupMaps(competition), [competition]);
  const rows = useMemo(() => buildPricingRows(competition, maps), [competition, maps]);
  const visibleRows = useMemo(
    () => filterPricingRows(rows, filters, deferredSearch),
    [rows, filters, deferredSearch],
  );
  const stats = useMemo(() => buildPricingStats(competition), [competition]);
  const warnings = useMemo(() => buildPricingWarnings(competition), [competition]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "a") {
        const target = event.target as HTMLElement | null;
        if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
        event.preventDefault();
        setSelected(new Set(visibleRows.map((row) => row.key)));
      }
      if (event.key === "Escape") {
        setSelected(new Set());
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [visibleRows]);

  if (isLoading) {
    return <PricingSkeleton />;
  }

  const apiErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof ApiError) {
      return error.problem?.detail ?? fallback;
    }
    return fallback;
  };

  const handleSelectChange = (key: string, next: boolean): void => {
    setSelected((current) => {
      const copy = new Set(current);
      if (next) copy.add(key);
      else copy.delete(key);
      return copy;
    });
  };

  const handleSavePrice = async (
    row: PricingRow,
    amount: string,
    currency: string,
    calculationType: "PER_PARTICIPANT" | "PER_PERFORMANCE",
  ): Promise<void> => {
    onAutosaveStateChange("saving");
    setSavingKey(row.key);
    try {
      await upsertPrice.mutateAsync({
        competitionId: competition.id,
        payload: {
          categoryId: row.rule.categoryId,
          disciplineId: row.rule.disciplineId,
          ageCategoryId: row.rule.ageCategoryId,
          participantGroupId: row.rule.participantGroupId,
          participationFormatId: row.rule.participationFormatId,
          amount,
          currency,
          calculationType,
          mode: row.price ? "change" : "add",
        },
      });
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось сохранить цену"));
    } finally {
      setSavingKey(null);
    }
  };

  const runBulk = async (operation: BulkPriceOperation): Promise<void> => {
    const plan = planBulkPricingMutations(rows, selected, operation);
    if (plan.upserts.length === 0 && plan.removes.length === 0) {
      toast.error("Нет изменений для выбранных правил");
      return;
    }

    onAutosaveStateChange("saving");
    try {
      const result = await bulkPricing.mutateAsync({
        competitionId: competition.id,
        upserts: plan.upserts.map((item) => ({
          ...item,
          mode: item.mode,
        })),
        removes: plan.removes,
      });
      toast.success(
        [
          result.updated > 0 ? `${result.updated} обновлено` : null,
          result.removed > 0 ? `${result.removed} удалено` : null,
          result.failed > 0 ? `${result.failed} ошибок` : null,
        ]
          .filter(Boolean)
          .join(" · ") || "Готово",
      );
      setBulkMode(null);
      setSelected(new Set());
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось выполнить массовую операцию"));
    }
  };

  const runCopy = async (
    dimension: CopyPricingDimension,
    sourceId: string,
    targetId: string,
  ): Promise<void> => {
    const plan = planCopyPricing(competition, dimension, sourceId, targetId);
    const upserts = copyPlanToMutations(plan);
    if (upserts.length === 0) {
      toast.error("Нечего копировать для выбранных значений");
      return;
    }
    onAutosaveStateChange("saving");
    try {
      const result = await bulkPricing.mutateAsync({
        competitionId: competition.id,
        upserts,
        removes: [],
      });
      toast.success(
        `${result.updated} скопировано` +
          (plan.skippedNoTarget > 0 ? ` · ${plan.skippedNoTarget} без цели` : ""),
      );
      setCopyOpen(false);
      onAutosaveStateChange("saved");
    } catch (error) {
      onAutosaveStateChange("error");
      toast.error(apiErrorMessage(error, "Не удалось скопировать цены"));
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

  const hasAdmissionRules = competition.admissionRules.length > 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Раздел только для просмотра">
              Цены можно изменять только в статусах «Черновик» и «Настроен».
            </Alert>
          ) : null}

          {!hasAdmissionRules ? (
            <Alert variant="warning" title="Сначала создайте правила допуска">
              Цены задаются только для существующих комбинаций допуска.
            </Alert>
          ) : null}

          <PerformanceDiscountCard competition={competition} disabled={isReadOnly} />

          <PageSection
            title="Цены"
            description="Цены необязательны: комбинация без цены остаётся доступной для подачи и не входит в сумму заявки. Для заданной цены выберите тип расчёта: за участника (цена × число участников) или за номер (фиксированная сумма)."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-base">Цены по правилам допуска</CardTitle>
                  {!isReadOnly && hasAdmissionRules ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setCopyOpen(true)}
                    >
                      <Copy className="size-3.5" aria-hidden="true" />
                      Копировать цены
                    </Button>
                  ) : null}
                </div>

                {hasAdmissionRules ? (
                  <div className="space-y-3">
                    <Input
                      label="Поиск"
                      placeholder="Жанр, номинация, возраст, группа, формат, цена"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      leadingIcon={<Search aria-hidden="true" />}
                    />
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                      {filterSelect(
                        "Жанр",
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
                        "Номинация",
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
                        competition.ageCategories.map((item) => ({
                          value: item.id,
                          label: item.name,
                        })),
                        (ageCategoryId) => setFilters((current) => ({ ...current, ageCategoryId })),
                      )}
                      {filterSelect(
                        "Группа",
                        filters.participantGroupId,
                        competition.participantGroups.map((item) => ({
                          value: item.id,
                          label: item.name,
                        })),
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
                      {filterSelect(
                        "Статус цены",
                        filters.priceStatus,
                        [
                          { value: "configured", label: "Заданы" },
                          { value: "missing", label: "Без цены" },
                        ],
                        (priceStatus) =>
                          setFilters((current) => ({
                            ...current,
                            priceStatus: priceStatus as "configured" | "missing" | null,
                          })),
                      )}
                    </div>
                  </div>
                ) : null}
              </CardHeader>

              <CardContent className="space-y-3">
                {!isReadOnly && hasAdmissionRules ? (
                  <PricingBulkToolbar
                    selectedCount={selected.size}
                    visibleCount={visibleRows.length}
                    disabled={bulkPricing.isPending}
                    onSelectAllVisible={() =>
                      setSelected(new Set(visibleRows.map((row) => row.key)))
                    }
                    onClearSelection={() => setSelected(new Set())}
                    onOpenBulk={setBulkMode}
                    onOpenCopy={() => setCopyOpen(true)}
                  />
                ) : null}

                {!hasAdmissionRules ? (
                  <EmptyState
                    icon={<CircleDollarSign />}
                    title="Нет правил допуска"
                    description="Создайте комбинации в разделе «Правила допуска», затем задайте цены здесь."
                    action={
                      <Button type="button" onClick={() => onNavigateSection("admission-rules")}>
                        К правилам допуска
                      </Button>
                    }
                  />
                ) : visibleRows.length === 0 ? (
                  <EmptyState title="Ничего не найдено" description="Измените поиск или фильтры." />
                ) : (
                  <ul
                    className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
                    aria-label="Цены по правилам допуска"
                  >
                    {visibleRows.map((row) => (
                      <PricingCard
                        key={row.key}
                        row={row}
                        selected={selected.has(row.key)}
                        readOnly={isReadOnly}
                        saving={savingKey === row.key}
                        onSelectChange={handleSelectChange}
                        onSavePrice={handleSavePrice}
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
              <CardTitle className="text-base">Сводка цен</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <StatRow label="Правил допуска" value={String(stats.admissionRules)} />
              <StatRow label="Цен задано" value={String(stats.configuredPrices)} />
              <StatRow label="Без цены" value={String(stats.missingPrices)} />
              <StatRow label="Готовность" value={`${stats.completionPercent}%`} />
              <StatRow label="За участника" value={String(stats.perParticipantCount)} />
              <StatRow label="За номер" value={String(stats.perPerformanceCount)} />
              <StatRow
                label="Средняя"
                value={
                  stats.averagePrice == null
                    ? "—"
                    : `${formatAmount(stats.averagePrice)} ${stats.currency}`
                }
              />
              <StatRow
                label="Мин."
                value={
                  stats.lowestPrice == null
                    ? "—"
                    : `${formatAmount(stats.lowestPrice)} ${stats.currency}`
                }
              />
              <StatRow
                label="Макс."
                value={
                  stats.highestPrice == null
                    ? "—"
                    : `${formatAmount(stats.highestPrice)} ${stats.currency}`
                }
              />
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

      <PricingBulkDialog
        open={bulkMode != null}
        mode={bulkMode ?? "set"}
        selectedCount={selected.size}
        submitting={bulkPricing.isPending}
        onOpenChange={(open) => {
          if (!open) setBulkMode(null);
        }}
        onApply={runBulk}
      />

      <PricingCopyDialog
        open={copyOpen}
        competition={competition}
        submitting={bulkPricing.isPending}
        onOpenChange={setCopyOpen}
        onApply={runCopy}
      />
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
