import { useEffect, useMemo, useState } from "react";
import {
  allParticipantGroups,
  enabledParticipationFormats,
  formatAgeRangeLabel,
  formatParticipantRange,
  scopedAgeCategories,
  scopedDisciplines,
} from "@/features/competitions";
import type {
  _AdmissionRule,
  AddAdmissionRule,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Select,
} from "@/shared/ui";

interface EditAdmissionRuleDialogProps {
  open: boolean;
  competition: CompetitionDetail;
  rule: _AdmissionRule | null;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (previous: AddAdmissionRule, next: AddAdmissionRule) => Promise<void>;
}

export function EditAdmissionRuleDialog({
  open,
  competition,
  rule,
  submitting = false,
  onOpenChange,
  onSave,
}: EditAdmissionRuleDialogProps): React.JSX.Element {
  const [categoryId, setCategoryId] = useState("");
  const [disciplineId, setDisciplineId] = useState("");
  const [ageCategoryId, setAgeCategoryId] = useState("");
  const [participantGroupId, setParticipantGroupId] = useState("");
  const [participationFormatId, setParticipationFormatId] = useState("");

  useEffect(() => {
    if (!open || !rule) return;
    setCategoryId(rule.categoryId);
    setDisciplineId(rule.disciplineId);
    setAgeCategoryId(rule.ageCategoryId);
    setParticipantGroupId(rule.participantGroupId);
    setParticipationFormatId(rule.participationFormatId);
  }, [open, rule]);

  const disciplines = categoryId ? scopedDisciplines(competition, categoryId) : [];
  const groups = allParticipantGroups(competition);
  // Age categories belong to a participant group, so scope ages by the chosen group.
  const ages = participantGroupId ? scopedAgeCategories(competition, participantGroupId) : [];
  const formats = enabledParticipationFormats(competition);

  const ageCountByGroup = useMemo(() => {
    const counts = new Map<string, number>();
    for (const age of competition.ageCategories) {
      counts.set(age.participantGroupId, (counts.get(age.participantGroupId) ?? 0) + 1);
    }
    return counts;
  }, [competition.ageCategories]);
  // A group with no age categories cannot form a rule (a rule always needs an age).
  const groupHasNoAges = Boolean(participantGroupId) && ages.length === 0;

  const nominations = useMemo(
    () =>
      [...competition.categories].sort(
        (a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"),
      ),
    [competition.categories],
  );

  const canSave =
    Boolean(categoryId) &&
    Boolean(disciplineId) &&
    Boolean(ageCategoryId) &&
    Boolean(participantGroupId) &&
    Boolean(participationFormatId) &&
    rule != null;

  const handleCategoryChange = (nextCategoryId: string): void => {
    setCategoryId(nextCategoryId);
    // Category scopes disciplines only; groups and ages are competition-wide.
    setDisciplineId("");
  };

  const handleGroupChange = (nextGroupId: string): void => {
    setParticipantGroupId(nextGroupId);
    // The age category must belong to the chosen group; clear it otherwise.
    const stillValid = competition.ageCategories.some(
      (item) => item.id === ageCategoryId && item.participantGroupId === nextGroupId,
    );
    if (!stillValid) {
      setAgeCategoryId("");
    }
  };

  const handleSave = async (): Promise<void> => {
    if (!rule || !canSave) return;
    await onSave(
      {
        categoryId: rule.categoryId,
        disciplineId: rule.disciplineId,
        ageCategoryId: rule.ageCategoryId,
        participantGroupId: rule.participantGroupId,
        participationFormatId: rule.participationFormatId,
      },
      {
        categoryId,
        disciplineId,
        ageCategoryId,
        participantGroupId,
        participationFormatId,
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Редактировать правило</DialogTitle>
          <DialogDescription>
            Измените комбинацию. Старое правило будет заменено новым.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-1">
          <Select
            label="Жанр"
            value={categoryId}
            onValueChange={handleCategoryChange}
            options={nominations.map((item) => ({ value: item.id, label: item.name }))}
            placeholder="Выберите жанр"
          />
          <Select
            label="Номинация"
            value={disciplineId}
            onValueChange={setDisciplineId}
            options={disciplines.map((item) => ({ value: item.id, label: item.name }))}
            placeholder="Выберите номинацию"
            disabled={!categoryId}
          />
          <Select
            label="Группа участников"
            value={participantGroupId}
            onValueChange={handleGroupChange}
            options={groups.map((item) => {
              const ageCount = ageCountByGroup.get(item.id) ?? 0;
              const range = formatParticipantRange(item.minCount, item.maxCount);
              return {
                value: item.id,
                label:
                  ageCount === 0
                    ? `${item.name} (${range}) · нет возрастных`
                    : `${item.name} (${range})`,
              };
            })}
            placeholder="Выберите группу"
          />
          <div className="space-y-1">
            <Select
              label="Возрастная категория"
              value={ageCategoryId}
              onValueChange={setAgeCategoryId}
              options={ages.map((item) => ({
                value: item.id,
                label: `${item.name} (${formatAgeRangeLabel(item.minAge, item.maxAge)})`,
              }))}
              placeholder="Выберите возраст"
              disabled={!participantGroupId || groupHasNoAges}
            />
            {groupHasNoAges ? (
              <p className="text-warning text-xs">
                В этой группе нет возрастных категорий — добавьте их в разделе «Возрастные
                категории», чтобы создать правило.
              </p>
            ) : null}
          </div>
          <Select
            label="Формат участия"
            value={participationFormatId}
            onValueChange={setParticipationFormatId}
            options={formats.map((item) => ({ value: item.id, label: item.name }))}
            placeholder="Выберите формат"
          />
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button
            type="button"
            loading={submitting}
            disabled={!canSave || submitting}
            onClick={() => void handleSave()}
          >
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
