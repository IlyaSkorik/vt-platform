import { useState } from "react";
import type { BulkPriceOperation, PricingCalculationTypeValue } from "@/features/competitions";
import {
  DEFAULT_CALCULATION_TYPE,
  PRICING_CALCULATION_TYPE_OPTIONS,
  parseAmount,
} from "@/features/competitions";
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

type BulkMode =
  | "set"
  | "increase-percent"
  | "decrease-percent"
  | "increase-amount"
  | "decrease-amount"
  | "calculation-type"
  | "remove"
  | "template";

interface PricingBulkDialogProps {
  open: boolean;
  mode: BulkMode;
  selectedCount: number;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onApply: (operation: BulkPriceOperation) => Promise<void>;
}

const MODE_LABELS: Record<BulkMode, string> = {
  set: "Задать фиксированную цену",
  template: "Шаблон цены",
  "increase-percent": "Увеличить на %",
  "decrease-percent": "Уменьшить на %",
  "increase-amount": "Увеличить на сумму",
  "decrease-amount": "Уменьшить на сумму",
  "calculation-type": "Тип расчёта",
  remove: "Удалить цены",
};

export function PricingBulkDialog({
  open,
  mode,
  selectedCount,
  submitting = false,
  onOpenChange,
  onApply,
}: PricingBulkDialogProps): React.JSX.Element {
  const [value, setValue] = useState("");
  const [calculationType, setCalculationType] =
    useState<PricingCalculationTypeValue>(DEFAULT_CALCULATION_TYPE);
  const [error, setError] = useState<string | null>(null);

  const needsAmount = mode !== "remove" && mode !== "calculation-type";

  const handleApply = async (): Promise<void> => {
    if (mode === "remove") {
      await onApply({ type: "remove" });
      return;
    }

    if (mode === "calculation-type") {
      await onApply({ type: "set-calculation-type", calculationType });
      return;
    }

    const amount = parseAmount(value);
    if (amount == null) {
      setError("Введите значение больше нуля");
      return;
    }

    switch (mode) {
      case "set":
      case "template":
        await onApply({ type: "set", amount });
        break;
      case "increase-percent":
        await onApply({ type: "increase-percent", percent: amount });
        break;
      case "decrease-percent":
        await onApply({ type: "decrease-percent", percent: amount });
        break;
      case "increase-amount":
        await onApply({ type: "increase-amount", amount });
        break;
      case "decrease-amount":
        await onApply({ type: "decrease-amount", amount });
        break;
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setValue("");
          setCalculationType(DEFAULT_CALCULATION_TYPE);
          setError(null);
        }
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{MODE_LABELS[mode]}</DialogTitle>
          <DialogDescription>
            {mode === "calculation-type"
              ? `Выбрано правил: ${selectedCount}. Изменится только тип расчёта у комбинаций с уже заданной ценой.`
              : `Выбрано правил: ${selectedCount}. Тип расчёта (за участника / за номер) у каждой цены сохраняется.`}
          </DialogDescription>
        </DialogHeader>

        {mode === "calculation-type" ? (
          <Select
            label="Тип расчёта"
            value={calculationType}
            onValueChange={(next) => setCalculationType(next as PricingCalculationTypeValue)}
            options={PRICING_CALCULATION_TYPE_OPTIONS}
          />
        ) : needsAmount ? (
          <Input
            label={
              mode.includes("percent")
                ? "Процент"
                : mode === "template" || mode === "set"
                  ? "Цена"
                  : "Сумма"
            }
            inputMode="decimal"
            value={value}
            error={error}
            onChange={(event) => {
              setValue(event.target.value);
              setError(null);
            }}
          />
        ) : (
          <p className="text-muted-foreground text-sm">
            Цены будут удалены у выбранных комбинаций. Сами правила допуска останутся.
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button
            type="button"
            variant={mode === "remove" ? "danger" : "primary"}
            loading={submitting}
            disabled={submitting || selectedCount === 0}
            onClick={() => void handleApply()}
          >
            Применить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface BulkToolbarProps {
  selectedCount: number;
  visibleCount: number;
  disabled?: boolean;
  onSelectAllVisible: () => void;
  onClearSelection: () => void;
  onOpenBulk: (mode: BulkMode) => void;
  onOpenCopy: () => void;
}

export function PricingBulkToolbar({
  selectedCount,
  visibleCount,
  disabled = false,
  onSelectAllVisible,
  onClearSelection,
  onOpenBulk,
  onOpenCopy,
}: BulkToolbarProps): React.JSX.Element | null {
  if (selectedCount === 0) return null;

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/95 px-3 py-2 shadow-sm backdrop-blur">
      <span className="mr-auto font-medium text-sm">Выбрано: {selectedCount}</span>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={onSelectAllVisible}
      >
        Все видимые ({visibleCount})
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={onClearSelection}
      >
        Снять
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("set")}
      >
        Цена
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("calculation-type")}
      >
        Тип оплаты
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("template")}
      >
        Шаблон
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("increase-percent")}
      >
        +%
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("decrease-percent")}
      >
        −%
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("increase-amount")}
      >
        +сумма
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("decrease-amount")}
      >
        −сумма
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={disabled}
        onClick={() => onOpenBulk("remove")}
      >
        Удалить
      </Button>
      <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={onOpenCopy}>
        Копировать
      </Button>
    </div>
  );
}

export type { BulkMode };
