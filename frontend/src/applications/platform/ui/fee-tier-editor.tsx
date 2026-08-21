/**
 * The per-performance price list, as the operator edits it.
 *
 * A row per band, in order, each asking only for the band's upper bound and its
 * price: the first band starts at one participant, every next one starts where the
 * previous ended, and the last is open-ended ("от N участников"). That is why the
 * lower bound is a label rather than a field — the schedule the backend demands
 * (gap-free, overlap-free, open at the top) is the only one this editor can produce.
 */
import { Plus, Trash2 } from "lucide-react";

import {
  addFeeTierDraft,
  exampleOrderTotal,
  FEE_CURRENCY,
  type FeeTierDraft,
  formatTierRange,
  removeFeeTierDraft,
  tierLowerBound,
  validateFeeTiers,
} from "@/applications/platform/lib/billing";
import { Button, IconButton, Input } from "@/shared/ui";

export function FeeTierEditor({
  drafts,
  onChange,
  disabled = false,
  showErrors = false,
}: {
  drafts: FeeTierDraft[];
  onChange: (next: FeeTierDraft[]) => void;
  disabled?: boolean;
  /** Errors stay quiet until the operator has tried to save once. */
  showErrors?: boolean;
}): React.JSX.Element {
  const { errors, tiers } = validateFeeTiers(drafts);
  const patch = (id: string, change: Partial<FeeTierDraft>): void => {
    onChange(drafts.map((draft) => (draft.id === id ? { ...draft, ...change } : draft)));
  };

  return (
    <div className="flex flex-col gap-3">
      <ul aria-label="Тарифная сетка" className="flex flex-col gap-3">
        {drafts.map((draft, index) => {
          const min = tierLowerBound(drafts, index);
          return (
            <li key={draft.id} className="flex flex-wrap items-end gap-2 sm:flex-nowrap">
              <span className="min-w-28 pb-2 text-muted-foreground text-sm">
                {draft.openEnded ? formatTierRange(min, null) : `от ${min} до`}
              </span>
              {draft.openEnded ? null : (
                <Input
                  label={index === 0 ? "Участников в номере" : undefined}
                  aria-label={`Верхняя граница правила ${index + 1}`}
                  type="number"
                  min={min}
                  className="sm:max-w-28"
                  disabled={disabled}
                  value={draft.maxParticipants}
                  error={showErrors ? errors[`${draft.id}.maxParticipants`] : undefined}
                  onChange={(event) => patch(draft.id, { maxParticipants: event.target.value })}
                />
              )}
              <Input
                label={index === 0 ? `Стоимость заявки, ${FEE_CURRENCY}` : undefined}
                aria-label={`Стоимость правила ${index + 1}`}
                inputMode="decimal"
                placeholder="2.50"
                className="sm:max-w-32"
                disabled={disabled}
                value={draft.amount}
                error={showErrors ? errors[`${draft.id}.amount`] : undefined}
                onChange={(event) => patch(draft.id, { amount: event.target.value })}
              />
              {draft.openEnded ? (
                <span className="pb-2 text-muted-foreground text-xs">
                  Последнее правило покрывает любой состав
                </span>
              ) : (
                <IconButton
                  type="button"
                  size="sm"
                  variant="ghost"
                  aria-label={`Удалить правило ${index + 1}`}
                  icon={<Trash2 className="size-3" aria-hidden="true" />}
                  disabled={disabled}
                  onClick={() => onChange(removeFeeTierDraft(drafts, draft.id))}
                />
              )}
            </li>
          );
        })}
      </ul>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() => onChange(addFeeTierDraft(drafts))}
        >
          <Plus className="size-4" />
          Добавить правило
        </Button>
        {tiers ? (
          <p className="text-muted-foreground text-xs">
            Пример: заказ из соло, дуэта и ансамбля из восьми человек —{" "}
            {exampleOrderTotal(tiers, [1, 2, 8])} {FEE_CURRENCY}
          </p>
        ) : null}
      </div>
    </div>
  );
}
