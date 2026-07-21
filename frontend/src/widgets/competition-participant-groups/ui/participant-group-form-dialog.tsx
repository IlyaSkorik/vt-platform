import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Textarea,
} from "@/shared/ui";

export interface ParticipantGroupFormValues {
  name: string;
  minCount: number;
  maxCount: number | null;
  description: string;
  openEnded: boolean;
}

interface ParticipantGroupFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  initialValues: ParticipantGroupFormValues;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: ParticipantGroupFormValues) => Promise<void>;
}

export function ParticipantGroupFormDialog({
  open,
  mode,
  initialValues,
  submitting,
  onOpenChange,
  onSubmit,
}: ParticipantGroupFormDialogProps): React.JSX.Element {
  const [name, setName] = useState(initialValues.name);
  const [minCount, setMinCount] = useState(String(initialValues.minCount));
  const [maxCount, setMaxCount] = useState(
    initialValues.maxCount != null ? String(initialValues.maxCount) : "",
  );
  const [openEnded, setOpenEnded] = useState(initialValues.openEnded);
  const [description, setDescription] = useState(initialValues.description);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setName(initialValues.name);
      setMinCount(String(initialValues.minCount));
      setMaxCount(initialValues.maxCount != null ? String(initialValues.maxCount) : "");
      setOpenEnded(initialValues.openEnded);
      setDescription(initialValues.description);
      setErrors({});
    }
  }, [open, initialValues]);

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!name.trim()) {
      next.name = "Обязательное поле";
    }
    const min = Number(minCount);
    if (Number.isNaN(min) || min < 1) {
      next.minCount = "Минимум — 1 участник";
    }
    if (!openEnded) {
      const max = Number(maxCount);
      if (Number.isNaN(max) || max < 1) {
        next.maxCount = "Укажите максимум или откройте диапазон";
      } else if (!next.minCount && min > max) {
        next.maxCount = "Максимум не может быть меньше минимума";
      }
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (!validate()) return;
    await onSubmit({
      name: name.trim(),
      minCount: Number(minCount),
      maxCount: openEnded ? null : Number(maxCount),
      description: description.trim(),
      openEnded,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-md flex-col gap-4 overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "create" ? "Новая группа участников" : "Редактирование группы участников"}
          </DialogTitle>
          <DialogDescription>
            Задайте название и диапазон численности. Диапазоны групп не должны пересекаться.
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex min-h-0 flex-1 flex-col gap-4"
          onSubmit={(e) => void handleSubmit(e)}
          noValidate
        >
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
            <Input
              label="Название"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={errors.name}
              placeholder="Solo, Duet, Ensemble…"
            />

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Мин. участников"
                type="number"
                required
                min={1}
                value={minCount}
                onChange={(e) => setMinCount(e.target.value)}
                error={errors.minCount}
              />
              <Input
                label="Макс. участников"
                type="number"
                min={1}
                value={openEnded ? "" : maxCount}
                disabled={openEnded}
                onChange={(e) => setMaxCount(e.target.value)}
                error={errors.maxCount}
                placeholder={openEnded ? "Без ограничения" : undefined}
              />
            </div>

            <Checkbox
              label="Открытый диапазон (N+)"
              checked={openEnded}
              onCheckedChange={(checked) => setOpenEnded(checked === true)}
            />

            <Textarea
              label="Описание"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Необязательно"
              rows={3}
            />
          </div>

          <DialogFooter className="shrink-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" loading={submitting}>
              {mode === "create" ? "Добавить" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
