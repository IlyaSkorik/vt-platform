import { GripVertical, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import {
  type AwardTier,
  type AwardTierInput,
  formatScore,
  type JudgingSetup,
  useReplaceAwardScale,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  IconButton,
  Input,
  toast,
} from "@/shared/ui";

/**
 * The festival's award scale: what it hands out, and for how many points.
 *
 * The one screen in this section that matters under *both* judging modes. A festival
 * running on protocols still needs its own vocabulary — one organizer awards "Лауреат I
 * степени" and the next "1 место" — and the protocol's dropdown is filled from here.
 * The bands are what online judging adds: without them nothing is decided by score.
 *
 * Edited as a whole list and saved as a whole list, because the rule that matters is a
 * property of the list rather than of any row: two tiers may not claim the same points.
 * The server is the one that decides that, and its message is shown as it comes.
 */

interface Row extends AwardTierInput {
  /** A key for React only. Tiers are identified by `code`, which may be blank until saved. */
  rowId: string;
}

function toRows(tiers: AwardTier[]): Row[] {
  return tiers.map((tier, index) => ({
    rowId: `${tier.code}-${index}`,
    code: tier.code,
    label: tier.label,
    minScore: tier.minScore,
    maxScore: tier.maxScore,
    sortOrder: index,
  }));
}

export function AwardScaleCard({
  setup,
  readOnly,
}: {
  setup: JudgingSetup;
  readOnly: boolean;
}): React.JSX.Element {
  const [rows, setRows] = useState<Row[]>(() => toRows(setup.awardScale));
  const [dirty, setDirty] = useState(false);
  const save = useReplaceAwardScale();

  useEffect(() => {
    // Only adopt the server's list while the organizer has nothing unsent: otherwise a
    // background refetch would throw away the band they are halfway through typing.
    if (!dirty) {
      setRows(toRows(setup.awardScale));
    }
  }, [setup.awardScale, dirty]);

  const edit = (rowId: string, patch: Partial<Row>): void => {
    setDirty(true);
    setRows((previous) =>
      previous.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)),
    );
  };

  const addTier = (): void => {
    setDirty(true);
    setRows((previous) => [
      ...previous,
      {
        rowId: `new-${previous.length}-${previous.length}`,
        // No code: the server mints one, and minting it here would risk two rows
        // claiming the same one.
        label: "",
        minScore: null,
        maxScore: null,
        sortOrder: previous.length,
      },
    ]);
  };

  const removeTier = (rowId: string): void => {
    setDirty(true);
    setRows((previous) => previous.filter((row) => row.rowId !== rowId));
  };

  const move = (rowId: string, direction: -1 | 1): void => {
    setRows((previous) => {
      const index = previous.findIndex((row) => row.rowId === rowId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= previous.length) return previous;
      const next = [...previous];
      const [moved] = next.splice(index, 1);
      if (moved == null) return previous;
      next.splice(target, 0, moved);
      setDirty(true);
      return next.map((row, position) => ({ ...row, sortOrder: position }));
    });
  };

  const handleSave = async (): Promise<void> => {
    const cleaned = rows
      .map((row, index) => ({
        code: row.code || undefined,
        label: row.label.trim(),
        minScore: row.minScore === "" ? null : row.minScore,
        maxScore: row.maxScore === "" ? null : row.maxScore,
        sortOrder: index,
      }))
      .filter((row) => row.label.length > 0);
    if (cleaned.length === 0) {
      toast.error("Шкала наград не может быть пустой");
      return;
    }
    try {
      await save.mutateAsync({ competitionId: setup.competitionId, tiers: cleaned });
      setDirty(false);
      toast.success("Шкала наград сохранена");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить шкалу наград");
    }
  };

  const handleReset = (): void => {
    setRows(toRows(setup.awardScale));
    setDirty(false);
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="gap-3 pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-base">Шкала наград</CardTitle>
            <CardDescription>
              Что фестиваль вручает и за сколько баллов. Одна шкала на весь фестиваль — так
              протокол, диплом и церемония называют награду одинаково.
            </CardDescription>
          </div>
          {!readOnly ? (
            <Button type="button" variant="outline" onClick={addTier}>
              <Plus className="size-4" aria-hidden="true" />
              Добавить ступень
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {setup.onlineJudging && !setup.scaleIsBanded ? (
          <Alert variant="warning" title="Диапазоны баллов не заданы">
            При онлайн-судействе награда определяется по баллам. Пока ни у одной ступени нет
            диапазона, жюри выставит оценки, а награды никто не получит.
          </Alert>
        ) : null}

        <div className="space-y-2">
          {rows.map((row, index) => (
            <div
              key={row.rowId}
              className="grid gap-2 rounded-lg border border-border p-3 sm:grid-cols-[auto_minmax(0,1fr)_7rem_7rem_auto] sm:items-end"
            >
              <div className="hidden flex-col sm:flex">
                <IconButton
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Поднять выше"
                  disabled={readOnly || index === 0}
                  onClick={() => move(row.rowId, -1)}
                  icon={<GripVertical className="size-4 rotate-180" aria-hidden="true" />}
                />
                <IconButton
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Опустить ниже"
                  disabled={readOnly || index === rows.length - 1}
                  onClick={() => move(row.rowId, 1)}
                  icon={<GripVertical className="size-4" aria-hidden="true" />}
                />
              </div>

              <Input
                label={index === 0 ? "Название награды" : undefined}
                placeholder="Лауреат I степени, 1 место, Гран-при…"
                value={row.label}
                disabled={readOnly}
                onChange={(event) => edit(row.rowId, { label: event.target.value })}
              />
              <Input
                label={index === 0 ? "От" : undefined}
                type="number"
                step="0.01"
                min={0}
                placeholder="—"
                value={row.minScore ?? ""}
                disabled={readOnly}
                onChange={(event) => edit(row.rowId, { minScore: event.target.value })}
              />
              <Input
                label={index === 0 ? "До" : undefined}
                type="number"
                step="0.01"
                min={0}
                placeholder="—"
                value={row.maxScore ?? ""}
                disabled={readOnly}
                onChange={(event) => edit(row.rowId, { maxScore: event.target.value })}
              />
              <IconButton
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Удалить «${row.label || "ступень"}»`}
                disabled={readOnly}
                onClick={() => removeTier(row.rowId)}
                icon={<Trash2 className="size-4 text-destructive" aria-hidden="true" />}
              />
            </div>
          ))}
        </div>

        <p className="text-muted-foreground text-xs">
          Диапазон можно оставить пустым с одной стороны: «от 95» — верхняя ступень без потолка, «до{" "}
          {formatScore("59.99")}» — нижняя без порога. Диапазоны не должны пересекаться.
        </p>

        {!readOnly ? (
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void handleSave()} loading={save.isPending}>
              Сохранить шкалу
            </Button>
            {dirty ? (
              <Button type="button" variant="ghost" onClick={handleReset}>
                Отменить изменения
              </Button>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
