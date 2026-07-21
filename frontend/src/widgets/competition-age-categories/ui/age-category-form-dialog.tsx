import { useEffect, useState } from "react";
import type { AgeCategoryKind, MixedAgeMethod } from "@/features/competitions/lib/age-categories";
import {
  AGE_CATEGORY_TYPE_OPTIONS,
  MIXED_AGE_METHOD_OPTIONS,
  suggestAgeCategoryName,
} from "@/features/competitions/lib/age-categories";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Select,
} from "@/shared/ui";

export interface AgeCategoryFormValues {
  participantGroupId: string;
  name: string;
  minAge: number;
  maxAge: number;
  type: AgeCategoryKind;
  mixedCalculationMethod: MixedAgeMethod | null;
}

interface AgeCategoryFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  groupName: string;
  initialValues: AgeCategoryFormValues;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: AgeCategoryFormValues) => Promise<void>;
}

export function AgeCategoryFormDialog({
  open,
  mode,
  groupName,
  initialValues,
  submitting,
  onOpenChange,
  onSubmit,
}: AgeCategoryFormDialogProps): React.JSX.Element {
  const [name, setName] = useState(initialValues.name);
  const [minAge, setMinAge] = useState(String(initialValues.minAge));
  const [maxAge, setMaxAge] = useState(String(initialValues.maxAge));
  const [type, setType] = useState<AgeCategoryKind>(initialValues.type);
  const [mixedMethod, setMixedMethod] = useState<MixedAgeMethod | null>(
    initialValues.mixedCalculationMethod,
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [localSubmitting, setLocalSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName(initialValues.name);
      setMinAge(String(initialValues.minAge));
      setMaxAge(String(initialValues.maxAge));
      setType(initialValues.type);
      setMixedMethod(initialValues.mixedCalculationMethod);
      setErrors({});
      setLocalSubmitting(false);
    }
  }, [open, initialValues]);

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!name.trim()) {
      next.name = "Обязательное поле";
    }
    const min = Number(minAge);
    const max = Number(maxAge);
    if (Number.isNaN(min) || min < 0) {
      next.minAge = "Укажите возраст от 0";
    }
    if (Number.isNaN(max) || max < 0 || max > 120) {
      next.maxAge = "Укажите возраст от 0 до 120";
    }
    if (!next.minAge && !next.maxAge && min > max) {
      next.maxAge = "Максимум не может быть меньше минимума";
    }
    if (type === "MIXED" && mixedMethod == null) {
      next.mixedMethod = "Выберите способ расчёта";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (submitting || localSubmitting) return;
    if (!validate()) return;
    setLocalSubmitting(true);
    try {
      await onSubmit({
        participantGroupId: initialValues.participantGroupId,
        name: name.trim(),
        minAge: Number(minAge),
        maxAge: Number(maxAge),
        type,
        mixedCalculationMethod: type === "MIXED" ? mixedMethod : null,
      });
    } finally {
      setLocalSubmitting(false);
    }
  };

  const handleSuggestName = (): void => {
    const min = Number(minAge);
    const max = Number(maxAge);
    if (!Number.isNaN(min) && !Number.isNaN(max) && min >= 0 && max >= min) {
      setName(suggestAgeCategoryName(min, max));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-md flex-col gap-4 overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "create"
              ? "Новая возрастная категория"
              : "Редактирование возрастной категории"}
          </DialogTitle>
          <DialogDescription>
            Укажите название и возрастной диапазон. Для открытых категорий вроде «26+» установите
            максимум 99 или выше.
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex min-h-0 flex-1 flex-col gap-4"
          onSubmit={(e) => void handleSubmit(e)}
          noValidate
        >
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-foreground">Группа участников</span>
              <span className="text-sm text-muted-foreground">{groupName}</span>
            </div>

            <Input
              label="Название"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={errors.name}
            />

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Мин. возраст"
                type="number"
                required
                min={0}
                max={120}
                value={minAge}
                onChange={(e) => setMinAge(e.target.value)}
                error={errors.minAge}
              />
              <Input
                label="Макс. возраст"
                type="number"
                required
                min={0}
                max={120}
                value={maxAge}
                onChange={(e) => setMaxAge(e.target.value)}
                error={errors.maxAge}
              />
            </div>

            <p className="text-muted-foreground text-xs">
              Если максимальный возраст 99 или больше, диапазон отображается как «N+».
            </p>

            <Button type="button" size="sm" variant="ghost" onClick={handleSuggestName}>
              Подставить название из диапазона
            </Button>

            <Select
              label="Тип категории"
              required
              options={[...AGE_CATEGORY_TYPE_OPTIONS]}
              value={type}
              onValueChange={(value) => {
                setType(value as AgeCategoryKind);
                if (value !== "MIXED") {
                  setMixedMethod(null);
                }
              }}
            />

            {type === "MIXED" ? (
              <Select
                label="Способ расчёта возраста"
                required
                options={[...MIXED_AGE_METHOD_OPTIONS]}
                {...(mixedMethod != null ? { value: mixedMethod } : {})}
                onValueChange={(value) => setMixedMethod(value as MixedAgeMethod)}
                error={errors.mixedMethod}
              />
            ) : null}
          </div>

          <DialogFooter className="shrink-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" loading={submitting || localSubmitting}>
              {mode === "create" ? "Добавить" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
