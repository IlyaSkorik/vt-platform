import { useEffect, useState } from "react";
import type {
  AdditionalServiceFormValues,
  ServiceBillingModelValue,
} from "@/features/competitions";
import {
  exampleServiceTotal,
  SERVICE_BILLING_MODEL_OPTIONS,
  validateAdditionalServiceForm,
} from "@/features/competitions";
import type { _ParticipationFormat } from "@/shared/api/generated/model-competitions";
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
  Select,
  Switch,
  Textarea,
} from "@/shared/ui";

interface AdditionalServiceFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  initialValues: AdditionalServiceFormValues;
  formats: _ParticipationFormat[];
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: AdditionalServiceFormValues) => Promise<void>;
}

export function AdditionalServiceFormDialog({
  open,
  mode,
  initialValues,
  formats,
  submitting,
  onOpenChange,
  onSubmit,
}: AdditionalServiceFormDialogProps): React.JSX.Element {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setValues(initialValues);
      setErrors({});
    }
  }, [open, initialValues]);

  const toggleFormat = (formatId: string, checked: boolean): void => {
    setValues((current) => {
      const next = new Set(current.participationFormatIds);
      if (checked) next.add(formatId);
      else next.delete(formatId);
      return { ...current, participationFormatIds: [...next] };
    });
    setErrors((current) => {
      const { participationFormatIds: _, ...rest } = current;
      return rest;
    });
  };

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    const nextErrors = validateAdditionalServiceForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    await onSubmit(values);
  };

  const preview =
    values.billingModel === "PER_PERFORMANCE"
      ? `Итого за номер = ${exampleServiceTotal(values.amount, 1, values.billingModel)} ${values.currency || "BYN"}`
      : `Соло 1× = ${exampleServiceTotal(values.amount, 1, values.billingModel)} · Дуэт 2× = ${exampleServiceTotal(values.amount, 2, values.billingModel)} ${values.currency || "BYN"}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-lg flex-col gap-4 overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "create" ? "Новая доп. услуга" : "Редактирование услуги"}
          </DialogTitle>
          <DialogDescription>
            Укажите цену, тип оплаты и форматы участия, для которых услуга доступна.
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex min-h-0 flex-1 flex-col gap-4"
          onSubmit={(event) => void handleSubmit(event)}
          noValidate
        >
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
            <Input
              label="Название"
              required
              value={values.name}
              onChange={(event) =>
                setValues((current) => ({ ...current, name: event.target.value }))
              }
              error={errors.name}
              placeholder="Медаль, доставка, электронный диплом…"
            />

            <Textarea
              label="Описание"
              value={values.description}
              onChange={(event) =>
                setValues((current) => ({ ...current, description: event.target.value }))
              }
              placeholder="Необязательно"
              rows={3}
            />

            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Цена"
                required
                inputMode="decimal"
                value={values.amount}
                onChange={(event) =>
                  setValues((current) => ({ ...current, amount: event.target.value }))
                }
                error={errors.amount}
                placeholder="50.00"
              />
              <Input
                label="Валюта"
                value={values.currency}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    currency: event.target.value.toUpperCase(),
                  }))
                }
                placeholder="BYN"
              />
            </div>

            <Select
              label="Тип оплаты"
              value={values.billingModel}
              onValueChange={(next) =>
                setValues((current) => ({
                  ...current,
                  billingModel: next as ServiceBillingModelValue,
                }))
              }
              options={SERVICE_BILLING_MODEL_OPTIONS}
            />

            <p className="text-muted-foreground text-xs">{preview}</p>

            <fieldset className="space-y-2">
              <legend className="font-medium text-sm">
                Доступна для форматов <span className="text-destructive">*</span>
              </legend>
              {formats.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  Сначала создайте форматы участия в соответствующем разделе.
                </p>
              ) : (
                <div className="space-y-2 rounded-md border border-border p-3">
                  {formats.map((format) => (
                    <Checkbox
                      key={format.id}
                      size="sm"
                      label={format.enabled ? format.name : `${format.name} (выключен)`}
                      checked={values.participationFormatIds.includes(format.id)}
                      onCheckedChange={(checked) => toggleFormat(format.id, checked === true)}
                    />
                  ))}
                </div>
              )}
              {errors.participationFormatIds ? (
                <p className="text-destructive text-xs">{errors.participationFormatIds}</p>
              ) : null}
            </fieldset>

            <Switch
              label="Обязательная"
              description="Участник не сможет подать заявку без этой услуги"
              checked={values.required}
              onCheckedChange={(required) => setValues((current) => ({ ...current, required }))}
            />

            {mode === "create" ? (
              <Switch
                label="Включена"
                checked={values.enabled}
                onCheckedChange={(enabled) => setValues((current) => ({ ...current, enabled }))}
              />
            ) : null}
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
