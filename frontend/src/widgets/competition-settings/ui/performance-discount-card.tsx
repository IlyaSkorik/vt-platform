import { useCallback, useEffect, useRef, useState } from "react";
import {
  defaultCompetitionSettings,
  mergeSettingsWithFormats,
  settingsToUpdatePayload,
  useUpdateCompetitionSettingsMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  toast,
} from "@/shared/ui";

const AUTOSAVE_DELAY_MS = 500;

interface PerformanceDiscountCardProps {
  competition: CompetitionDetail;
  disabled?: boolean;
}

/**
 * The repeat-performance discount, shown with the prices it modifies.
 *
 * Stored on the competition's settings but presented here rather than in «Правила
 * участия»: it is a number that changes what an order costs, and an organizer
 * looking for it looks under prices. Owns its own debounced save so the pricing
 * section does not have to learn how settings are persisted.
 */
export function PerformanceDiscountCard({
  competition,
  disabled = false,
}: PerformanceDiscountCardProps): React.JSX.Element {
  const updateSettings = useUpdateCompetitionSettingsMutation();
  const stored = competition.settings?.additionalPerformanceDiscountPercent ?? 0;
  const [percent, setPercent] = useState(stored);
  const timer = useRef<number | null>(null);
  // The typed value the server has not been told about yet, so leaving the section
  // mid-debounce sends it rather than discarding it with the timer.
  const pending = useRef<number | null>(null);

  useEffect(() => {
    setPercent(stored);
  }, [stored]);

  const persist = useCallback(
    async (next: number) => {
      if (pending.current === next) {
        pending.current = null;
      }
      // The settings endpoint replaces the whole bag, so the current value has to be
      // sent alongside everything else rather than patched on its own.
      const base = mergeSettingsWithFormats(
        competition.settings ?? defaultCompetitionSettings(),
        competition.participationFormats ?? [],
      );
      try {
        await updateSettings.mutateAsync({
          competitionId: competition.id,
          payload: settingsToUpdatePayload({ ...base, additionalPerformanceDiscountPercent: next }),
        });
      } catch (error) {
        setPercent(stored);
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось сохранить скидку")
            : "Не удалось сохранить скидку";
        toast.error(message);
      }
    },
    [competition, updateSettings, stored],
  );

  const persistRef = useRef(persist);
  useEffect(() => {
    persistRef.current = persist;
  }, [persist]);

  useEffect(
    () => () => {
      if (timer.current != null) {
        window.clearTimeout(timer.current);
        timer.current = null;
      }
      const unsaved = pending.current;
      if (unsaved != null) {
        pending.current = null;
        void persistRef.current(unsaved);
      }
    },
    [],
  );

  const onChange = (raw: string): void => {
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return;
    const next = Math.max(0, Math.min(100, Math.round(parsed)));
    setPercent(next);
    pending.current = next;
    if (timer.current != null) {
      window.clearTimeout(timer.current);
    }
    timer.current = window.setTimeout(() => {
      timer.current = null;
      void persist(next);
    }, AUTOSAVE_DELAY_MS);
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Скидка за несколько выступлений</CardTitle>
        <CardDescription>
          Применяется автоматически ко 2-му и следующим выступлениям в одной заявке. Не действует,
          если заявка претендует на льготу.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Input
          label="Скидка на 2-е и следующие выступления (%)"
          type="number"
          min={0}
          max={100}
          value={String(percent)}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
      </CardContent>
    </Card>
  );
}
