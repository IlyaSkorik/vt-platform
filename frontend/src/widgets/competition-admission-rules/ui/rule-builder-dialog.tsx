import { ArrowLeft, ArrowRight, Check, Layers } from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";
import {
  type AdmissionRuleDraft,
  ageCategoryGroupMap,
  allParticipantGroups,
  canAdvanceBuilderStep,
  cartesianCount,
  emptyAdmissionRuleDraft,
  enabledParticipationFormats,
  formatAgeRangeLabel,
  formatParticipantRange,
  planBulkAdmissionRules,
  scopedAgeCategories,
  scopedDisciplines,
  toggleId,
} from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui";

const STEPS = [
  { id: 1, title: "Жанр" },
  { id: 2, title: "Номинации" },
  { id: 3, title: "Группы участников" },
  { id: 4, title: "Возрастные категории" },
  { id: 5, title: "Форматы участия" },
  { id: 6, title: "Создание" },
] as const;

interface RuleBuilderDialogProps {
  open: boolean;
  competition: CompetitionDetail;
  initialDraft?: AdmissionRuleDraft;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (draft: AdmissionRuleDraft) => Promise<void>;
}

export function RuleBuilderDialog({
  open,
  competition,
  initialDraft,
  submitting = false,
  onOpenChange,
  onCreate,
}: RuleBuilderDialogProps): React.JSX.Element {
  const titleId = useId();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<AdmissionRuleDraft>(emptyAdmissionRuleDraft());

  useEffect(() => {
    if (!open) return;
    setDraft(initialDraft ?? emptyAdmissionRuleDraft());
    setStep(initialDraft?.categoryId ? 2 : 1);
  }, [open, initialDraft]);

  const existingKeys = useMemo(
    () =>
      new Set(
        competition.admissionRules.map(
          (rule) =>
            `${rule.categoryId}|${rule.disciplineId}|${rule.ageCategoryId}|${rule.participantGroupId}|${rule.participationFormatId}`,
        ),
      ),
    [competition.admissionRules],
  );

  const ageGroupOf = useMemo(() => ageCategoryGroupMap(competition), [competition]);
  // How many age categories each group has — a group without any cannot take part in
  // an admission rule (a rule always needs an age category), so it is offered disabled.
  const ageCountByGroup = useMemo(() => {
    const counts = new Map<string, number>();
    for (const age of competition.ageCategories) {
      counts.set(age.participantGroupId, (counts.get(age.participantGroupId) ?? 0) + 1);
    }
    return counts;
  }, [competition.ageCategories]);
  const plan = useMemo(
    () => planBulkAdmissionRules(draft, existingKeys, ageGroupOf),
    [draft, existingKeys, ageGroupOf],
  );
  const previewCount = cartesianCount(draft, ageGroupOf);
  const canNext = canAdvanceBuilderStep(step, draft);

  const disciplines = draft.categoryId ? scopedDisciplines(competition, draft.categoryId) : [];
  const groups = allParticipantGroups(competition);
  // Age categories belong to a group, so only offer ages of the selected group(s).
  const ages = draft.participantGroupIds.flatMap((groupId) =>
    scopedAgeCategories(competition, groupId),
  );
  const formats = enabledParticipationFormats(competition);

  const nominations = useMemo(
    () =>
      [...competition.categories].sort(
        (a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"),
      ),
    [competition.categories],
  );

  const selectCategory = (categoryId: string): void => {
    setDraft({
      categoryId,
      disciplineIds: [],
      ageCategoryIds: [],
      participantGroupIds: [],
      participationFormatIds: draft.participationFormatIds,
    });
  };

  const goNext = (): void => {
    if (!canNext || step >= STEPS.length) return;
    setStep((current) => current + 1);
  };

  const goBack = (): void => {
    if (step <= 1) return;
    setStep((current) => current - 1);
  };

  const handleCreate = async (): Promise<void> => {
    if (plan.toCreate.length === 0 && plan.skippedExisting === 0) return;
    await onCreate(draft);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[90vh] max-w-2xl flex-col gap-0 overflow-hidden p-0"
        aria-labelledby={titleId}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.metaKey && !event.ctrlKey) {
            const target = event.target as HTMLElement;
            if (target.tagName === "BUTTON" || target.tagName === "INPUT") return;
            if (step < STEPS.length && canNext) {
              event.preventDefault();
              goNext();
            }
          }
        }}
      >
        <DialogHeader className="border-border border-b px-6 py-4">
          <DialogTitle id={titleId}>Конструктор правил допуска</DialogTitle>
          <DialogDescription>
            Выберите комбинации — система создаст все уникальные правила автоматически.
          </DialogDescription>
        </DialogHeader>

        <nav
          aria-label="Шаги конструктора"
          className="flex gap-1 overflow-x-auto border-border border-b px-4 py-3"
        >
          {STEPS.map((item) => {
            const active = item.id === step;
            const done = item.id < step;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  if (item.id < step || (item.id === step + 1 && canNext)) {
                    setStep(item.id);
                  }
                }}
                className={cn(
                  "shrink-0 rounded-md px-2.5 py-1.5 text-xs transition-colors",
                  active && "bg-primary text-primary-foreground",
                  done && !active && "bg-muted text-foreground",
                  !active && !done && "text-muted-foreground",
                )}
              >
                {item.id}. {item.title}
              </button>
            );
          })}
        </nav>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {step === 1 ? (
            <div className="space-y-3">
              <p className="text-muted-foreground text-sm">Выберите жанр.</p>
              <ul className="grid gap-2 sm:grid-cols-2">
                {nominations.map((item) => {
                  const selected = draft.categoryId === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => selectCategory(item.id)}
                        className={cn(
                          "w-full rounded-lg border px-3 py-3 text-left transition-all",
                          selected
                            ? "border-primary bg-primary/5 shadow-sm"
                            : "border-border hover:border-primary/40",
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-sm">{item.name}</span>
                          {selected ? (
                            <Check className="size-4 text-primary" aria-hidden="true" />
                          ) : null}
                        </div>
                        {item.description ? (
                          <p className="mt-1 line-clamp-2 text-muted-foreground text-xs">
                            {item.description}
                          </p>
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {step === 2 ? (
            <MultiSelectStep
              title="Номинации этого жанра"
              empty="В жанре нет номинаций."
              items={disciplines.map((item) => ({
                id: item.id,
                label: item.name,
              }))}
              selectedIds={draft.disciplineIds}
              onChange={(ids) => setDraft((current) => ({ ...current, disciplineIds: ids }))}
            />
          ) : null}

          {step === 3 ? (
            <MultiSelectStep
              title="Группы участников"
              empty="Нет групп участников. Сначала создайте их в разделе «Группы участников»."
              items={groups.map((item) => {
                const ageCount = ageCountByGroup.get(item.id) ?? 0;
                return {
                  id: item.id,
                  label: `${item.name} (${formatParticipantRange(item.minCount, item.maxCount)})`,
                  disabled: ageCount === 0,
                  description:
                    ageCount === 0
                      ? "Нет возрастных категорий — добавьте их в разделе «Возрастные категории»"
                      : `${ageCount} ${pluralAge(ageCount)}`,
                };
              })}
              selectedIds={draft.participantGroupIds}
              onChange={(ids) =>
                setDraft((current) => ({
                  ...current,
                  participantGroupIds: ids,
                  // Drop ages that no longer belong to any selected group.
                  ageCategoryIds: current.ageCategoryIds.filter((ageId) => {
                    const groupId = ageGroupOf.get(ageId);
                    return groupId != null && ids.includes(groupId);
                  }),
                }))
              }
            />
          ) : null}

          {step === 4 ? (
            <MultiSelectStep
              title="Возрастные категории выбранных групп"
              empty="Нет возрастных категорий для выбранных групп участников."
              items={ages.map((item) => ({
                id: item.id,
                label: `${item.name} (${formatAgeRangeLabel(item.minAge, item.maxAge)})`,
              }))}
              selectedIds={draft.ageCategoryIds}
              onChange={(ids) => setDraft((current) => ({ ...current, ageCategoryIds: ids }))}
            />
          ) : null}

          {step === 5 ? (
            <MultiSelectStep
              title="Форматы участия"
              empty="Нет включённых форматов участия."
              items={formats.map((item) => {
                const row: { id: string; label: string; description?: string } = {
                  id: item.id,
                  label: item.name,
                };
                if (item.description) {
                  row.description = item.description;
                }
                return row;
              })}
              selectedIds={draft.participationFormatIds}
              onChange={(ids) =>
                setDraft((current) => ({ ...current, participationFormatIds: ids }))
              }
            />
          ) : null}

          {step === 6 ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Layers className="size-4 text-primary" aria-hidden="true" />
                  <p className="font-medium text-sm">Итог массового создания</p>
                </div>
                <dl className="grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-muted-foreground">Комбинаций</dt>
                    <dd className="font-semibold text-lg">{previewCount}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Будет создано</dt>
                    <dd className="font-semibold text-lg text-success">{plan.toCreate.length}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Уже есть</dt>
                    <dd className="font-semibold text-lg">{plan.skippedExisting}</dd>
                  </div>
                </dl>
              </div>
              <p className="text-muted-foreground text-sm">
                {draft.disciplineIds.length} дисц. × {draft.ageCategoryIds.length} возр. ×{" "}
                {draft.participantGroupIds.length} групп × {draft.participationFormatIds.length}{" "}
                форматов
              </p>
              {plan.toCreate.length === 0 ? (
                <p className="text-warning text-sm">
                  Все выбранные комбинации уже существуют. Измените выбор или закройте конструктор.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>

        <DialogFooter className="border-border border-t px-6 py-4">
          <div className="flex w-full flex-wrap items-center justify-between gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={goBack}
              disabled={step === 1 || submitting}
            >
              <ArrowLeft className="size-3.5" aria-hidden="true" />
              Назад
            </Button>
            {step < STEPS.length ? (
              <Button type="button" onClick={goNext} disabled={!canNext || submitting}>
                Далее
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Button>
            ) : (
              <Button
                type="button"
                loading={submitting}
                disabled={plan.toCreate.length === 0 || submitting}
                onClick={() => void handleCreate()}
              >
                Создать правила
                {plan.toCreate.length > 0 ? ` (${plan.toCreate.length})` : ""}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface MultiSelectStepProps {
  title: string;
  empty: string;
  items: Array<{ id: string; label: string; description?: string; disabled?: boolean }>;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

function MultiSelectStep({
  title,
  empty,
  items,
  selectedIds,
  onChange,
}: MultiSelectStepProps): React.JSX.Element {
  if (items.length === 0) {
    return <p className="text-muted-foreground text-sm">{empty}</p>;
  }

  const selectableItems = items.filter((item) => !item.disabled);
  const allSelected =
    selectableItems.length > 0 && selectableItems.every((item) => selectedIds.includes(item.id));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">{title}</p>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          disabled={selectableItems.length === 0}
          onClick={() => {
            onChange(allSelected ? [] : selectableItems.map((item) => item.id));
          }}
        >
          {allSelected ? "Снять все" : "Выбрать все"}
        </Button>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {items.map((item) => {
          const checked = selectedIds.includes(item.id);
          const disabled = item.disabled === true;
          return (
            <li key={item.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  if (!disabled) {
                    onChange(toggleId(selectedIds, item.id));
                  }
                }}
                className={cn(
                  "flex w-full items-start gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors",
                  disabled
                    ? "cursor-not-allowed border-dashed border-border bg-muted/30 opacity-70"
                    : checked
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/40",
                )}
                aria-pressed={checked}
              >
                <span
                  className={cn(
                    "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border",
                    checked && !disabled
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background",
                  )}
                  aria-hidden="true"
                >
                  {checked && !disabled ? <Check className="size-3" /> : null}
                </span>
                <span className="min-w-0">
                  <span className="block font-medium text-sm">{item.label}</span>
                  {item.description ? (
                    <span
                      className={cn(
                        "mt-0.5 block text-xs",
                        disabled ? "text-warning" : "text-muted-foreground",
                      )}
                    >
                      {item.description}
                    </span>
                  ) : null}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function pluralAge(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "возрастная категория";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "возрастные категории";
  return "возрастных категорий";
}
