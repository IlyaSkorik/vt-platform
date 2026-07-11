import { useMemo, useState } from "react";
import type { CopyPricingDimension } from "@/features/competitions";
import { planCopyPricing } from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
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

interface PricingCopyDialogProps {
  open: boolean;
  competition: CompetitionDetail;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onApply: (dimension: CopyPricingDimension, sourceId: string, targetId: string) => Promise<void>;
}

const DIMENSION_OPTIONS: Array<{ value: CopyPricingDimension; label: string }> = [
  { value: "format", label: "Формат участия" },
  { value: "group", label: "Группа участников" },
  { value: "age", label: "Возрастная категория" },
  { value: "nomination", label: "Номинация целиком" },
];

export function PricingCopyDialog({
  open,
  competition,
  submitting = false,
  onOpenChange,
  onApply,
}: PricingCopyDialogProps): React.JSX.Element {
  const [dimension, setDimension] = useState<CopyPricingDimension>("format");
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  const options = useMemo(() => {
    switch (dimension) {
      case "format":
        return competition.participationFormats.map((item) => ({
          value: item.id,
          label: item.name,
        }));
      case "group":
        return competition.participantGroups.map((item) => ({
          value: item.id,
          label: item.name,
        }));
      case "age":
        return competition.ageCategories.map((item) => ({
          value: item.id,
          label: item.name,
        }));
      case "nomination":
        return competition.categories.map((item) => ({
          value: item.id,
          label: item.name,
        }));
    }
  }, [competition, dimension]);

  const preview = useMemo(() => {
    if (!sourceId || !targetId) return null;
    return planCopyPricing(competition, dimension, sourceId, targetId);
  }, [competition, dimension, sourceId, targetId]);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setSourceId("");
          setTargetId("");
        }
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Копировать цены</DialogTitle>
          <DialogDescription>
            Скопируйте цены с одного значения измерения на другое для совпадающих комбинаций.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <Select
            label="Измерение"
            value={dimension}
            onValueChange={(value) => {
              setDimension(value as CopyPricingDimension);
              setSourceId("");
              setTargetId("");
            }}
            options={DIMENSION_OPTIONS}
          />
          <Select
            label="Откуда"
            value={sourceId}
            onValueChange={setSourceId}
            options={options}
            placeholder="Источник"
          />
          <Select
            label="Куда"
            value={targetId}
            onValueChange={setTargetId}
            options={options}
            placeholder="Назначение"
          />
          {preview ? (
            <p className="text-muted-foreground text-sm">
              Будет обновлено: {preview.items.length}. Без цели: {preview.skippedNoTarget}. Без цены
              источника: {preview.skippedNoSourcePrice}.
            </p>
          ) : null}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button
            type="button"
            loading={submitting}
            disabled={!sourceId || !targetId || sourceId === targetId || submitting}
            onClick={() => void onApply(dimension, sourceId, targetId)}
          >
            Копировать
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
