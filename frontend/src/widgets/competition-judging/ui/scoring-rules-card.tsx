import { Copy, ExternalLink } from "lucide-react";

import {
  AGGREGATION_LABELS,
  type AggregationMethod,
  type BoardReveal,
  type BoardVisibility,
  DIMENSION_LABELS,
  type JudgingSetup,
  REVEAL_LABELS,
  type TallyDimension,
  useUpdateBoardSettings,
  useUpdateScoringRules,
  useUpdateTallyScope,
  VISIBILITY_LABELS,
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
  Checkbox,
  Radio,
  RadioGroup,
  Switch,
  toast,
} from "@/shared/ui";

/**
 * The three settings that decide what the numbers mean and who sees them.
 *
 * Grouped into one file because they are one decision in three parts: how a panel's
 * sheets become an act's score, which acts that score is announced beside, and how much
 * of the working the hall is shown. Each saves on change — there is nothing here to
 * coalesce and nothing to lose by an organizer walking away.
 */

const AGGREGATIONS: AggregationMethod[] = ["AVERAGE", "SUM"];
const DIMENSIONS: TallyDimension[] = [
  "CATEGORY",
  "DISCIPLINE",
  "AGE_CATEGORY",
  "PARTICIPATION_FORMAT",
];
const VISIBILITIES: BoardVisibility[] = ["PER_JUDGE", "TOTAL_ONLY"];
const REVEALS: BoardReveal[] = ["IMMEDIATE", "AFTER_CLOSE"];

/** One choice, with the sentence that explains what choosing it costs. */
function Choice({
  value,
  label,
  description,
}: {
  value: string;
  label: string;
  description: string;
}): React.JSX.Element {
  return (
    <div className="rounded-lg border border-border p-3 transition-colors hover:bg-muted/40">
      <Radio value={value} label={label} description={description} />
    </div>
  );
}

export function ScoringRulesCard({
  setup,
  readOnly,
}: {
  setup: JudgingSetup;
  readOnly: boolean;
}): React.JSX.Element {
  const saveRules = useUpdateScoringRules();

  const update = async (patch: {
    aggregation?: AggregationMethod;
    dropHighest?: boolean;
    dropLowest?: boolean;
  }): Promise<void> => {
    try {
      await saveRules.mutateAsync({
        competitionId: setup.competitionId,
        aggregation: patch.aggregation ?? setup.aggregation,
        dropHighest: patch.dropHighest ?? setup.dropHighest,
        dropLowest: patch.dropLowest ?? setup.dropLowest,
      });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить правила");
    }
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Подсчёт баллов</CardTitle>
        <CardDescription>
          Как из оценок нескольких судей получается один балл выступления.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <RadioGroup
          className="space-y-2"
          value={setup.aggregation}
          disabled={readOnly}
          onValueChange={(next) => void update({ aggregation: next as AggregationMethod })}
        >
          {AGGREGATIONS.map((value) => (
            <Choice
              key={value}
              value={value}
              label={AGGREGATION_LABELS[value]}
              description={
                value === "AVERAGE"
                  ? "Балл остаётся в той же шкале, что и лист одного судьи, — диапазоны наград не поплывут, если кто-то из жюри не приедет."
                  : "«Набрано 47 баллов из 50». Зависит от числа судей: диапазоны наград надо задавать под весь состав."
              }
            />
          ))}
        </RadioGroup>

        <div className="space-y-2 border-border border-t pt-3">
          <p className="font-medium text-sm">Отбрасывать крайние оценки</p>
          <p className="text-muted-foreground text-xs">
            Классическая защита от одного судьи, решающего исход. Работает, только когда после
            отбрасывания остаётся не меньше трёх оценок.
          </p>
          <div className="flex flex-wrap gap-4">
            <Checkbox
              label="Высшую"
              checked={setup.dropHighest}
              disabled={readOnly}
              onCheckedChange={(next) => void update({ dropHighest: Boolean(next) })}
            />
            <Checkbox
              label="Низшую"
              checked={setup.dropLowest}
              disabled={readOnly}
              onCheckedChange={(next) => void update({ dropLowest: Boolean(next) })}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function TallyScopeCard({
  setup,
  readOnly,
}: {
  setup: JudgingSetup;
  readOnly: boolean;
}): React.JSX.Element {
  const save = useUpdateTallyScope();

  const toggle = async (dimension: TallyDimension, on: boolean): Promise<void> => {
    const next = on
      ? [...new Set([...setup.tallyDimensions, dimension])]
      : setup.tallyDimensions.filter((item) => item !== dimension);
    try {
      await save.mutateAsync({ competitionId: setup.competitionId, dimensions: next });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить разрез");
    }
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Разрез итогов</CardTitle>
        <CardDescription>
          По каким измерениям итоги разносятся на отдельные ведомости и объявляются. Награда
          определяется баллами в любом случае — разрез решает, кого объявляют вместе.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {DIMENSIONS.map((dimension) => (
          <Checkbox
            key={dimension}
            label={DIMENSION_LABELS[dimension]}
            description={
              dimension === "CATEGORY" ? "Всегда включён: протокол — документ жанра." : undefined
            }
            checked={setup.tallyDimensions.includes(dimension)}
            disabled={readOnly || dimension === "CATEGORY"}
            onCheckedChange={(next) => void toggle(dimension, Boolean(next))}
          />
        ))}
      </CardContent>
    </Card>
  );
}

export function BoardSettingsCard({
  setup,
  readOnly,
}: {
  setup: JudgingSetup;
  readOnly: boolean;
}): React.JSX.Element {
  const save = useUpdateBoardSettings();

  const update = async (patch: {
    enabled?: boolean;
    visibility?: BoardVisibility;
    reveal?: BoardReveal;
    showAward?: boolean;
    showRunningOrder?: boolean;
  }): Promise<void> => {
    try {
      await save.mutateAsync({
        competitionId: setup.competitionId,
        enabled: patch.enabled ?? setup.boardEnabled,
        visibility: patch.visibility ?? setup.boardVisibility,
        reveal: patch.reveal ?? setup.boardReveal,
        showAward: patch.showAward ?? setup.boardShowAward,
        showRunningOrder: patch.showRunningOrder ?? setup.boardShowRunningOrder,
      });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить табло");
    }
  };

  const boardUrl = setup.boardPath != null ? `${window.location.origin}${setup.boardPath}` : null;

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Табло в зале</CardTitle>
        <CardDescription>
          Экран у сцены с оценками в реальном времени. Открывается по ссылке без входа — выведите
          его на проектор.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Switch
          label="Показывать табло"
          description="Выключите — ссылка перестанет открываться, и последние оценки исчезнут с экрана."
          checked={setup.boardEnabled}
          disabled={readOnly}
          onCheckedChange={(next) => void update({ enabled: Boolean(next) })}
        />

        {setup.boardEnabled ? (
          <>
            {boardUrl != null ? (
              <Alert variant="info" title="Ссылка на табло">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="min-w-0 flex-1 break-all rounded bg-muted px-2 py-1 text-xs">
                    {boardUrl}
                  </code>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      void navigator.clipboard.writeText(boardUrl);
                      toast.success("Ссылка скопирована");
                    }}
                  >
                    <Copy className="size-4" aria-hidden="true" />
                    Копировать
                  </Button>
                  <Button type="button" size="sm" variant="ghost" asChild>
                    <a href={boardUrl} target="_blank" rel="noreferrer">
                      <ExternalLink className="size-4" aria-hidden="true" />
                      Открыть
                    </a>
                  </Button>
                </div>
              </Alert>
            ) : null}

            <RadioGroup
              className="space-y-2"
              label="Что показывать"
              value={setup.boardVisibility}
              disabled={readOnly}
              onValueChange={(next) => void update({ visibility: next as BoardVisibility })}
            >
              {VISIBILITIES.map((value) => (
                <Choice
                  key={value}
                  value={value}
                  label={VISIBILITY_LABELS[value]}
                  description={
                    value === "PER_JUDGE"
                      ? "Как в фигурном катании: фамилия судьи и его балл. Максимально прозрачно и максимально открыто для жюри."
                      : "Зал видит «оценено 3 из 5» и итоговый балл. Кто сколько поставил — не показывается."
                  }
                />
              ))}
            </RadioGroup>

            <RadioGroup
              className="space-y-2"
              label="Когда показывать"
              value={setup.boardReveal}
              disabled={readOnly}
              onValueChange={(next) => void update({ reveal: next as BoardReveal })}
            >
              {REVEALS.map((value) => (
                <Choice
                  key={value}
                  value={value}
                  label={REVEAL_LABELS[value]}
                  description={
                    value === "IMMEDIATE"
                      ? "Балл загорается сразу. Зрелищно, но судья уже не исправит опечатку незаметно."
                      : "Оценки появляются, когда ведущий закрывает выступление, — ровно тогда же они перестают меняться."
                  }
                />
              ))}
            </RadioGroup>

            <div className="space-y-2 border-border border-t pt-3">
              <Switch
                label="Показывать награду"
                description="Под баллом — ступень, которую он даёт по шкале наград."
                checked={setup.boardShowAward}
                disabled={readOnly}
                onCheckedChange={(next) => void update({ showAward: Boolean(next) })}
              />
              <Switch
                label="Показывать предыдущие номера"
                description="Под текущим выступлением — несколько уже оценённых."
                checked={setup.boardShowRunningOrder}
                disabled={readOnly}
                onCheckedChange={(next) => void update({ showRunningOrder: Boolean(next) })}
              />
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
