import { ChevronDown, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import {
  type CriteriaSet,
  type Criterion,
  type CriterionInput,
  formatScore,
  type JudgingScope,
  type JudgingSetup,
  useReplaceCriteria,
} from "@/features/judging";
import { ApiError } from "@/shared/api";
import { cn } from "@/shared/lib";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  IconButton,
  Input,
  toast,
} from "@/shared/ui";

/**
 * The criteria a jury is given, per genre and — where a genre is not uniform — per
 * nomination.
 *
 * A nomination's sheet **replaces** its genre's rather than adding to it, and the card
 * says so where an organizer will read it: merging two lists would leave them unable to
 * drop an inherited criterion, and a judge unable to tell which sheet they are on.
 *
 * Criteria keep their ids across a save. That is not a detail — a mark already given
 * points at a criterion, so renaming "Техника" must not orphan it.
 */

interface DraftCriterion extends CriterionInput {
  rowId: string;
}

function toDraft(criteria: Criterion[]): DraftCriterion[] {
  return criteria.map((item, index) => ({
    rowId: item.id,
    id: item.id,
    name: item.name,
    maxScore: item.maxScore,
    weight: item.weight,
    sortOrder: index,
    description: item.description,
  }));
}

function blankCriterion(index: number): DraftCriterion {
  return {
    rowId: `new-${index}-${Math.random().toString(36).slice(2, 8)}`,
    name: "",
    maxScore: "10",
    weight: "1",
    sortOrder: index,
  };
}

function maxTotalOf(rows: DraftCriterion[]): string {
  const total = rows.reduce((sum, row) => sum + Number(row.maxScore) * Number(row.weight), 0);
  return Number.isFinite(total) ? total.toFixed(2) : "0";
}

function CriteriaEditor({
  competitionId,
  scope,
  targetId,
  targetName,
  existing,
  readOnly,
  onDone,
}: {
  competitionId: string;
  scope: JudgingScope;
  targetId: string;
  targetName: string;
  existing: CriteriaSet | undefined;
  readOnly: boolean;
  onDone: () => void;
}): React.JSX.Element {
  const [rows, setRows] = useState<DraftCriterion[]>(() =>
    existing != null ? toDraft(existing.criteria) : [blankCriterion(0)],
  );
  const save = useReplaceCriteria();

  const edit = (rowId: string, patch: Partial<DraftCriterion>): void => {
    setRows((previous) =>
      previous.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)),
    );
  };

  const handleSave = async (): Promise<void> => {
    const cleaned = rows
      .map((row, index) => ({
        // `id` present means "this is the same criterion" — the marks stay attached.
        id: row.id,
        name: row.name.trim(),
        maxScore: row.maxScore,
        weight: row.weight,
        sortOrder: index,
        description: row.description ?? null,
      }))
      .filter((row) => row.name.length > 0);
    try {
      await save.mutateAsync({ competitionId, scope, targetId, criteria: cleaned });
      toast.success(cleaned.length === 0 ? "Критерии убраны" : "Критерии сохранены");
      onDone();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить критерии");
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-sm">
          Критерии: {targetName}
          {scope === "DISCIPLINE" ? (
            <span className="ml-2 font-normal text-muted-foreground text-xs">
              заменят критерии жанра для этой номинации
            </span>
          ) : null}
        </p>
        <Badge variant="secondary">Максимум {formatScore(maxTotalOf(rows))} балла(ов)</Badge>
      </div>

      <div className="space-y-2">
        {rows.map((row, index) => (
          <div
            key={row.rowId}
            className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_6rem_6rem_auto] sm:items-end"
          >
            <Input
              label={index === 0 ? "Критерий" : undefined}
              placeholder="Техника исполнения"
              value={row.name}
              disabled={readOnly}
              onChange={(event) => edit(row.rowId, { name: event.target.value })}
            />
            <Input
              label={index === 0 ? "Макс. балл" : undefined}
              type="number"
              step="0.01"
              min={0.01}
              value={row.maxScore}
              disabled={readOnly}
              onChange={(event) => edit(row.rowId, { maxScore: event.target.value })}
            />
            <Input
              label={index === 0 ? "Вес" : undefined}
              type="number"
              step="0.01"
              min={0.01}
              value={row.weight}
              disabled={readOnly}
              onChange={(event) => edit(row.rowId, { weight: event.target.value })}
            />
            <IconButton
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Удалить критерий «${row.name || "новый"}»`}
              disabled={readOnly}
              onClick={() =>
                setRows((previous) => previous.filter((item) => item.rowId !== row.rowId))
              }
              icon={<Trash2 className="size-4 text-destructive" aria-hidden="true" />}
            />
          </div>
        ))}
      </div>

      <p className="text-muted-foreground text-xs">
        Вес — во сколько раз критерий важнее остальных. Балл судьи за номер = сумма оценок,
        умноженных на вес.
      </p>

      {!readOnly ? (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setRows((previous) => [...previous, blankCriterion(previous.length)])}
          >
            <Plus className="size-4" aria-hidden="true" />
            Критерий
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => void handleSave()}
            loading={save.isPending}
          >
            Сохранить
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onDone}>
            Закрыть
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export function CriteriaCard({
  setup,
  readOnly,
}: {
  setup: JudgingSetup;
  readOnly: boolean;
}): React.JSX.Element {
  const [open, setOpen] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ scope: JudgingScope; targetId: string } | null>(null);

  const setsByTarget = useMemo(() => {
    const map = new Map<string, CriteriaSet>();
    for (const item of setup.criteriaSets) {
      map.set(`${item.scope}:${item.targetId}`, item);
    }
    return map;
  }, [setup.criteriaSets]);

  if (setup.nominations.length === 0) {
    return (
      <Card className="shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Критерии оценки</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Сначала добавьте жанры"
            description="Критерии задаются для каждого жанра, поэтому сначала нужна структура фестиваля — раздел «Жанры и номинации»."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Критерии оценки</CardTitle>
        <CardDescription>
          Свой набор для каждого жанра. Если внутри жанра одна номинация судится иначе — задайте
          критерии ей: они заменят критерии жанра.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-2">
        {setup.nominations.map((nomination) => {
          const genreSet = setsByTarget.get(`CATEGORY:${nomination.categoryId}`);
          const isOpen = open === nomination.categoryId;
          return (
            <div key={nomination.categoryId} className="rounded-lg border border-border">
              <button
                type="button"
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
                onClick={() => setOpen(isOpen ? null : nomination.categoryId)}
                aria-expanded={isOpen}
              >
                <ChevronDown
                  className={cn("size-4 shrink-0 transition-transform", isOpen && "rotate-180")}
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1 truncate font-medium text-sm">
                  {nomination.name}
                </span>
                {genreSet != null ? (
                  <Badge variant="secondary">
                    {genreSet.criteria.length} крит. · до {formatScore(genreSet.maxTotal)}
                  </Badge>
                ) : (
                  <Badge variant="warning">Критериев нет</Badge>
                )}
              </button>

              {isOpen ? (
                <div className="space-y-2 border-border border-t p-3">
                  {editing?.scope === "CATEGORY" && editing.targetId === nomination.categoryId ? (
                    <CriteriaEditor
                      competitionId={setup.competitionId}
                      scope="CATEGORY"
                      targetId={nomination.categoryId}
                      targetName={nomination.name}
                      existing={genreSet}
                      readOnly={readOnly}
                      onDone={() => setEditing(null)}
                    />
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="min-w-0 flex-1 text-muted-foreground text-sm">
                        {genreSet != null
                          ? genreSet.criteria.map((item) => item.name).join(" · ")
                          : "Жюри нечего заполнять в этом жанре."}
                      </p>
                      {!readOnly ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setEditing({ scope: "CATEGORY", targetId: nomination.categoryId })
                          }
                        >
                          {genreSet != null ? "Изменить" : "Задать критерии"}
                        </Button>
                      ) : null}
                    </div>
                  )}

                  {nomination.disciplines.length > 0 ? (
                    <div className="space-y-1.5 border-border border-t pt-2">
                      <p className="font-semibold text-muted-foreground text-xs uppercase tracking-wide">
                        Номинации с отдельными критериями
                      </p>
                      {nomination.disciplines.map((discipline) => {
                        const own = setsByTarget.get(`DISCIPLINE:${discipline.id}`);
                        const isEditing =
                          editing?.scope === "DISCIPLINE" && editing.targetId === discipline.id;
                        return (
                          <div key={discipline.id} className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="min-w-0 flex-1 truncate text-sm">
                                {discipline.name}
                              </span>
                              {own != null ? (
                                <Badge variant="secondary">свои критерии</Badge>
                              ) : (
                                <span className="text-muted-foreground text-xs">как у жанра</span>
                              )}
                              {!readOnly && !isEditing ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() =>
                                    setEditing({ scope: "DISCIPLINE", targetId: discipline.id })
                                  }
                                >
                                  {own != null ? "Изменить" : "Переопределить"}
                                </Button>
                              ) : null}
                            </div>
                            {isEditing ? (
                              <CriteriaEditor
                                competitionId={setup.competitionId}
                                scope="DISCIPLINE"
                                targetId={discipline.id}
                                targetName={discipline.name}
                                existing={own}
                                readOnly={readOnly}
                                onDone={() => setEditing(null)}
                              />
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
