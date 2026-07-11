import { ArrowDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { PricingCalculationTypeValue, PricingRow } from "@/features/competitions";
import {
  calculationTypeLabel,
  DEFAULT_CURRENCY,
  exampleTotalCost,
  normalizeCalculationType,
  PRICING_CALCULATION_TYPE_OPTIONS,
  parseAmount,
} from "@/features/competitions";
import { cn } from "@/shared/lib";
import { Badge, Input, Select } from "@/shared/ui";

const CHAIN_KEYS = ["nomination", "discipline", "age", "group", "format"] as const;

interface PricingCardProps {
  row: PricingRow;
  selected: boolean;
  readOnly?: boolean;
  saving?: boolean;
  onSelectChange: (key: string, selected: boolean) => void;
  onSavePrice: (
    row: PricingRow,
    amount: string,
    currency: string,
    calculationType: PricingCalculationTypeValue,
  ) => Promise<void>;
}

export function PricingCard({
  row,
  selected,
  readOnly = false,
  saving = false,
  onSelectChange,
  onSavePrice,
}: PricingCardProps): React.JSX.Element {
  const [draft, setDraft] = useState(row.price?.amount ?? "");
  const [calculationType, setCalculationType] = useState<PricingCalculationTypeValue>(
    normalizeCalculationType(row.price?.calculationType),
  );
  const [error, setError] = useState<string | null>(null);
  const lastSaved = useRef(
    `${row.price?.amount ?? ""}|${normalizeCalculationType(row.price?.calculationType)}`,
  );
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDraft(row.price?.amount ?? "");
    setCalculationType(normalizeCalculationType(row.price?.calculationType));
    lastSaved.current = `${row.price?.amount ?? ""}|${normalizeCalculationType(row.price?.calculationType)}`;
  }, [row.price?.amount, row.price?.calculationType]);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const chain = [
    row.labels.categoryName,
    row.labels.disciplineName,
    row.labels.ageCategoryName,
    row.labels.participantGroupName,
    row.labels.participationFormatName,
  ];

  const currency = row.price?.currency ?? DEFAULT_CURRENCY;
  const parsed = parseAmount(draft);
  const preview =
    parsed == null
      ? null
      : calculationType === "PER_PERFORMANCE"
        ? `Итого за номер = ${exampleTotalCost(parsed, 1, calculationType)} ${currency}`
        : `Соло 1× = ${exampleTotalCost(parsed, 1, calculationType)} · Дуэт 2× = ${exampleTotalCost(parsed, 2, calculationType)}`;

  const commit = async (
    value: string,
    nextType: PricingCalculationTypeValue = calculationType,
  ): Promise<void> => {
    if (readOnly) return;
    const amount = parseAmount(value);
    if (amount == null) {
      if (value.trim().length === 0) {
        setError(null);
        return;
      }
      setError("Цена должна быть больше нуля");
      return;
    }
    const normalized = amount.toFixed(2);
    const fingerprint = `${normalized}|${nextType}`;
    if (fingerprint === lastSaved.current) {
      setError(null);
      return;
    }
    setError(null);
    await onSavePrice(row, normalized, currency, nextType);
    lastSaved.current = fingerprint;
    setDraft(normalized);
    setCalculationType(nextType);
  };

  const scheduleSave = (value: string): void => {
    setDraft(value);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void commit(value);
    }, 650);
  };

  return (
    <li
      className={cn(
        "rounded-lg border bg-card p-3 transition-[border-color,box-shadow,opacity] duration-200",
        "[content-visibility:auto] [contain-intrinsic-size:auto_16rem]",
        row.status === "missing"
          ? "border-amber-300/80 shadow-[inset_3px_0_0_0_theme(colors.amber.500)]"
          : "border-border",
        selected && "ring-2 ring-primary/30",
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 rounded border-input"
            checked={selected}
            disabled={readOnly}
            onChange={(event) => onSelectChange(row.key, event.target.checked)}
            aria-label="Выбрать правило для массовых операций"
          />
          <Badge variant={row.status === "configured" ? "success" : "warning"} size="sm">
            {row.status === "configured" ? "Цена задана" : "Нет цены"}
          </Badge>
        </label>
        <span className="text-muted-foreground text-xs">{currency}</span>
      </div>

      <ol className="mb-3 space-y-1" aria-label="Комбинация допуска">
        {chain.map((label, index) => (
          <li key={CHAIN_KEYS[index] ?? label} className="min-w-0">
            {index > 0 ? (
              <ArrowDown className="mb-0.5 size-3 text-muted-foreground/70" aria-hidden="true" />
            ) : null}
            <p className="truncate font-medium text-sm leading-snug">{label}</p>
          </li>
        ))}
      </ol>

      <div className="space-y-3">
        <Select
          label="Тип расчёта"
          size="sm"
          value={calculationType}
          disabled={readOnly || saving}
          options={PRICING_CALCULATION_TYPE_OPTIONS}
          onValueChange={(value) => {
            const next = normalizeCalculationType(value);
            setCalculationType(next);
            if (draft.trim().length > 0) {
              void commit(draft, next);
            }
          }}
        />
        <Input
          label={calculationType === "PER_PERFORMANCE" ? "Цена за номер" : "Цена за участника"}
          inputMode="decimal"
          value={draft}
          disabled={readOnly || saving}
          error={error}
          description={
            preview ??
            (calculationType === "PER_PERFORMANCE"
              ? "Фиксированная стоимость номера, независимо от числа участников"
              : "Итоговая стоимость = цена × число участников")
          }
          onChange={(event) => scheduleSave(event.target.value)}
          onBlur={() => void commit(draft)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              if (timer.current) clearTimeout(timer.current);
              void commit(draft);
            }
          }}
        />
        {row.price ? (
          <p className="text-muted-foreground text-xs">{calculationTypeLabel(calculationType)}</p>
        ) : null}
      </div>
    </li>
  );
}
