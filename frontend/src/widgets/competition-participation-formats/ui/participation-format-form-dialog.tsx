import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Switch,
  Textarea,
} from "@/shared/ui";

export interface ParticipationFormatFormValues {
  name: string;
  description: string;
  enabled: boolean;
}

interface ParticipationFormatFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  initialValues: ParticipationFormatFormValues;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: ParticipationFormatFormValues) => Promise<void>;
}

export function ParticipationFormatFormDialog({
  open,
  mode,
  initialValues,
  submitting,
  onOpenChange,
  onSubmit,
}: ParticipationFormatFormDialogProps): React.JSX.Element {
  const [name, setName] = useState(initialValues.name);
  const [description, setDescription] = useState(initialValues.description);
  const [enabled, setEnabled] = useState(initialValues.enabled);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setName(initialValues.name);
      setDescription(initialValues.description);
      setEnabled(initialValues.enabled);
      setErrors({});
    }
  }, [open, initialValues]);

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!name.trim()) {
      next.name = "Обязательное поле";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (!validate()) return;
    await onSubmit({
      name: name.trim(),
      description: description.trim(),
      enabled,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-md flex-col gap-4 overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "create" ? "Новый формат участия" : "Редактирование формата участия"}
          </DialogTitle>
          <DialogDescription>
            Укажите, как участники могут выступать: очно, онлайн или ваш собственный вариант.
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
              placeholder="Очно, Онлайн, Hybrid…"
            />

            <Textarea
              label="Описание"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Необязательно"
              rows={3}
            />

            <Switch label="Включён" checked={enabled} onCheckedChange={setEnabled} />
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
