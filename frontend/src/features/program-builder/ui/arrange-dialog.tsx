/**
 * «Собрать программу» — форма, по которой программа составляется сама.
 *
 * Ручное составление выглядит так: «Добавить все», а потом сто строк мышью вверх-вниз,
 * перерывы на глаз и память о том, что Иванова в трёх номерах подряд. Эта форма — то же
 * самое, сказанное правилами: как сгруппировать день, кто открывает группу, где перерыв,
 * и сколько номеров должно разделять два выхода одного участника.
 *
 * Результат остаётся обычной программой: его правят теми же кнопками, что и собранный
 * руками. Поэтому форма и не пытается предусмотреть всё — она доводит до состояния, с
 * которого остаётся поправить две-три строки, а не выстроить сорок.
 *
 * Порядок признаков группировки — это и есть форма дня: «номинация → возраст» и «возраст
 * → номинация» дают разные фестивали. Поэтому признаки не просто отмечаются галочкой, а
 * выстраиваются в очередь, и очередь видна.
 */
import { ArrowDown, ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  IconButton,
  Input,
  Select,
} from "@/shared/ui";

import {
  type ArrangementSettings,
  arrangeInput,
  BREAK_RULE_LABELS,
  type BreakRule,
  DEFAULT_ARRANGEMENT,
  GROUPING_AXES,
  GROUPING_AXIS_LABELS,
  type GroupingAxis,
  PERFORMANCE_ORDER_LABELS,
  type PerformanceOrder,
} from "../model";

/** Сколько номеров между двумя выходами одного участника предлагает форма. */
const REPEAT_GAPS = [0, 2, 3, 5, 8] as const;

function gapLabel(gap: number): string {
  return gap === 0 ? "Не разводить" : `Не меньше ${gap} номеров между выходами`;
}

/** Минуты ↔ секунды: в форме часы и минуты, на проводе всегда секунды. */
function toMinutes(seconds: number | null | undefined, fallback: number): string {
  return String(Math.round((seconds ?? fallback) / 60));
}

function fromMinutes(value: string, fallback: number): number {
  const minutes = Number(value);
  return Number.isFinite(minutes) && minutes > 0 ? Math.round(minutes) * 60 : fallback;
}

export type ArrangeProgramDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Правила, по которым программу собирали в прошлый раз, — с них форма и открывается. */
  saved: ArrangementSettings | null;
  /** Идёт ли сборка: кнопка ждёт ответа, потому что он и есть новая программа. */
  pending: boolean;
  /**
   * Сколько строк сборка заменит.
   *
   * Ноль — программу собирают впервые, и терять нечего. Больше нуля — форма открыта
   * над уже расставленным днём, и «текущий порядок будет заменён» для него слишком
   * мягко: вместе со строками уходят подвинутые руками перерывы и заполненные ячейки.
   */
  replaces: number;
  onSubmit: (input: ReturnType<typeof arrangeInput>) => void;
};

export function ArrangeProgramDialog({
  open,
  onOpenChange,
  saved,
  pending,
  replaces,
  onSubmit,
}: ArrangeProgramDialogProps): React.JSX.Element {
  const [grouping, setGrouping] = useState<GroupingAxis[]>(DEFAULT_ARRANGEMENT.grouping);
  const [order, setOrder] = useState<PerformanceOrder>(DEFAULT_ARRANGEMENT.orderWithinGroup);
  const [breakRule, setBreakRule] = useState<BreakRule>(DEFAULT_ARRANGEMENT.breakRule);
  const [breakEveryMinutes, setBreakEveryMinutes] = useState("90");
  const [breakEveryItems, setBreakEveryItems] = useState("20");
  const [breakTitle, setBreakTitle] = useState("Перерыв");
  const [breakMinutes, setBreakMinutes] = useState("10");
  const [repeatGap, setRepeatGap] = useState(DEFAULT_ARRANGEMENT.repeatGap);
  const [openingTitle, setOpeningTitle] = useState("");
  const [openingMinutes, setOpeningMinutes] = useState("15");
  const [awardTitle, setAwardTitle] = useState("");
  const [awardMinutes, setAwardMinutes] = useState("30");

  // Форма наполняется при каждом открытии: программу могли пересобрать из другого места,
  // и диалог должен показывать правила, по которым стоит то, что сейчас на экране.
  useEffect(() => {
    if (!open) return;
    const source = saved ?? DEFAULT_ARRANGEMENT;
    setGrouping(source.grouping);
    setOrder(source.orderWithinGroup);
    setBreakRule(source.breakRule);
    setBreakEveryMinutes(toMinutes(source.breakAfterSeconds, 5400));
    setBreakEveryItems(String(source.breakAfterItems || 20));
    setBreakTitle(source.breakTitle ?? "Перерыв");
    setBreakMinutes(toMinutes(source.breakDurationSeconds, 600));
    setRepeatGap(source.repeatGap);
    setOpeningTitle(source.openingTitle ?? "");
    setOpeningMinutes(toMinutes(source.openingDurationSeconds, 900));
    setAwardTitle(source.awardTitle ?? "");
    setAwardMinutes(toMinutes(source.awardDurationSeconds, 1800));
  }, [open, saved]);

  const toggleAxis = (axis: GroupingAxis) => {
    setGrouping((previous) =>
      previous.includes(axis)
        ? previous.filter((item) => item !== axis)
        : // Новый признак встаёт последним: он уточняет уже выбранные, а не главнее их.
          [...previous, axis],
    );
  };

  const moveAxis = (index: number, delta: number) => {
    setGrouping((previous) => {
      const next = [...previous];
      const target = index + delta;
      if (target < 0 || target >= next.length) return previous;
      const [moved] = next.splice(index, 1);
      next.splice(target, 0, moved as GroupingAxis);
      return next;
    });
  };

  const submit = () => {
    onSubmit(
      arrangeInput({
        grouping,
        orderWithinGroup: order,
        breakRule,
        breakAfterSeconds: fromMinutes(breakEveryMinutes, 5400),
        breakAfterItems: Math.max(1, Number(breakEveryItems) || 20),
        breakTitle: breakTitle.trim() || "Перерыв",
        breakDurationSeconds: fromMinutes(breakMinutes, 600),
        repeatGap,
        openingTitle: openingTitle.trim() || null,
        openingDurationSeconds: fromMinutes(openingMinutes, 900),
        awardTitle: awardTitle.trim() || null,
        awardDurationSeconds: fromMinutes(awardMinutes, 1800),
      }),
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Собрать программу</DialogTitle>
          <DialogDescription>
            Программа соберётся из всех допущенных выступлений этой программы. Текущий порядок будет
            заменён — после сборки его можно править как обычно.
            {replaces > 0 ? (
              <>
                {" "}
                Сейчас в программе строк: {replaces}. Все они будут заменены: перерывы, которые вы
                подвинули руками, изменённая длительность номеров и заполненные ячейки пропадут.
                Колонки останутся.
              </>
            ) : null}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <section aria-label="Группировка" className="space-y-3">
            <div>
              <p className="font-medium text-sm">Как сгруппировать день</p>
              <p className="text-muted-foreground text-xs">
                Порядок признаков — это и есть форма дня: сначала делим по первому, внутри — по
                второму.
              </p>
            </div>
            <div className="space-y-1.5">
              {grouping.map((axis, index) => (
                <div
                  key={axis}
                  data-testid="arrange-axis"
                  className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2"
                >
                  <span className="text-sm">
                    <span className="text-muted-foreground">{index + 1}.</span>{" "}
                    {GROUPING_AXIS_LABELS[axis]}
                  </span>
                  <span className="flex items-center gap-1">
                    <IconButton
                      aria-label="Выше"
                      icon={<ArrowUp className="size-3.5" />}
                      variant="ghost"
                      size="sm"
                      disabled={index === 0}
                      onClick={() => moveAxis(index, -1)}
                    />
                    <IconButton
                      aria-label="Ниже"
                      icon={<ArrowDown className="size-3.5" />}
                      variant="ghost"
                      size="sm"
                      disabled={index === grouping.length - 1}
                      onClick={() => moveAxis(index, 1)}
                    />
                  </span>
                </div>
              ))}
              {grouping.length === 0 ? (
                <p className="text-muted-foreground text-xs">
                  Без группировки: один сплошной порядок.
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {GROUPING_AXES.map((axis) => (
                <Checkbox
                  key={axis}
                  label={GROUPING_AXIS_LABELS[axis]}
                  checked={grouping.includes(axis)}
                  onCheckedChange={() => toggleAxis(axis)}
                />
              ))}
            </div>
          </section>

          <Select
            label="Порядок внутри группы"
            value={order}
            onValueChange={(value: string) => setOrder(value as PerformanceOrder)}
            options={Object.entries(PERFORMANCE_ORDER_LABELS).map(([value, label]) => ({
              value,
              label,
            }))}
          />

          <Select
            label="Повторы одного участника"
            value={String(repeatGap)}
            onValueChange={(value: string) => setRepeatGap(Number(value))}
            options={REPEAT_GAPS.map((gap) => ({ value: String(gap), label: gapLabel(gap) }))}
            description="Считается по участникам номера. Педагог и организация не в счёт — студия привозит двадцать номеров, и разводить их значит разводить весь день."
          />

          <section aria-label="Перерывы" className="space-y-3">
            <Select
              label="Перерывы"
              value={breakRule}
              onValueChange={(value: string) => setBreakRule(value as BreakRule)}
              options={Object.entries(BREAK_RULE_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              description="Отделение — это то, что лежит между двумя перерывами."
            />
            {breakRule === "EVERY_DURATION" ? (
              <Input
                label="Отделение не длиннее, минут"
                type="number"
                min={1}
                value={breakEveryMinutes}
                onChange={(event) => setBreakEveryMinutes(event.target.value)}
              />
            ) : null}
            {breakRule === "EVERY_COUNT" ? (
              <Input
                label="Перерыв через каждые N номеров"
                type="number"
                min={1}
                value={breakEveryItems}
                onChange={(event) => setBreakEveryItems(event.target.value)}
              />
            ) : null}
            {breakRule !== "NONE" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Название перерыва"
                  value={breakTitle}
                  onChange={(event) => setBreakTitle(event.target.value)}
                />
                <Input
                  label="Длительность, минут"
                  type="number"
                  min={1}
                  value={breakMinutes}
                  onChange={(event) => setBreakMinutes(event.target.value)}
                />
              </div>
            ) : null}
          </section>

          <section aria-label="Открытие и награждение" className="space-y-3">
            <div>
              <p className="font-medium text-sm">Открытие и награждение</p>
              <p className="text-muted-foreground text-xs">
                Назовите блок, чтобы он встал в программу. Пустое название — блока не будет.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Открытие"
                placeholder="Например, «Открытие фестиваля»"
                value={openingTitle}
                onChange={(event) => setOpeningTitle(event.target.value)}
              />
              <Input
                label="Длительность, минут"
                type="number"
                min={1}
                value={openingMinutes}
                onChange={(event) => setOpeningMinutes(event.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Награждение"
                placeholder="Например, «Награждение»"
                value={awardTitle}
                onChange={(event) => setAwardTitle(event.target.value)}
              />
              <Input
                label="Длительность, минут"
                type="number"
                min={1}
                value={awardMinutes}
                onChange={(event) => setAwardMinutes(event.target.value)}
              />
            </div>
          </section>

          <Alert variant="warning">
            Сборка заменит текущий порядок целиком. Вставленные вручную перерывы, изменённые
            длительности и значения, вписанные в свои колонки, придётся задать заново — сами колонки
            останутся.
          </Alert>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button onClick={submit} loading={pending}>
            Собрать программу
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
