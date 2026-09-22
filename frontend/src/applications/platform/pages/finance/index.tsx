import { Trash2, Wallet } from "lucide-react";
import { useMemo, useState } from "react";

import {
  EXPENSE_CATEGORIES,
  EXPENSE_CATEGORY_LABELS,
  type ExpenseCategory,
  type PlatformExpense,
  refusalMessage,
  useAmendExpense,
  usePlatformDashboard,
  usePlatformExpenses,
  usePlatformOrganizations,
  useRecordExpense,
  useRemoveExpense,
} from "@/applications/platform/api/platform-api";
import { formatMoney } from "@/applications/platform/lib/billing";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  LoadingState,
  Select,
  Textarea,
  toast,
} from "@/shared/ui";

/** The value the organization pickers use for "the platform itself". */
const PLATFORM_ITSELF = "";

function categoryLabel(category: string): string {
  return EXPENSE_CATEGORY_LABELS[category as ExpenseCategory] ?? category;
}

/** A stored `YYYY-MM-DD` as a person reads it. */
function formatDay(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.valueOf())
    ? value
    : parsed.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

/** Today, in the format the date input and the API both speak. */
function today(): string {
  const now = new Date();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function StatTile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "positive" | "negative";
}): React.JSX.Element {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 py-4">
        <span className="text-muted-foreground text-xs uppercase tracking-wide">{label}</span>
        <span
          className={
            tone === "negative"
              ? "font-semibold text-2xl text-destructive"
              : tone === "positive"
                ? "font-semibold text-2xl text-success"
                : "font-semibold text-2xl"
          }
        >
          {value}
        </span>
        {hint ? <span className="text-muted-foreground text-xs">{hint}</span> : null}
      </CardContent>
    </Card>
  );
}

/**
 * Income, costs and the difference — across the whole platform, for all time.
 *
 * Sits above the filters because nothing below them applies to it: the filters
 * narrow the ledger, and a bottom line narrowed to March would be a bottom line
 * only for March's costs against every month's commission.
 *
 * Both differences are shown. "Получено" is commission that has actually been
 * paid; "ожидается" is what the same books come to once every outstanding order
 * settles. An operator who is behind on one and ahead on the other is looking at
 * a collection problem, and one figure would hide which.
 */
function BottomLine(): React.JSX.Element {
  const dashboard = usePlatformDashboard("", "");
  const data = dashboard.data;

  const tiles: Array<{
    label: string;
    value: string;
    hint: string;
    tone?: "positive" | "negative";
  }> = [
    {
      label: "Комиссия получена",
      value: data ? formatMoney(data.settledCommission) : "—",
      hint: "Доля платформы от оплаченных заявок",
    },
    {
      label: "Расходы",
      value: data ? formatMoney(data.expenses) : "—",
      hint: data ? `${formatMoney(data.unattributedExpenses)} — общие, без организации` : "",
    },
    {
      label: "Разница",
      value: data ? formatMoney(data.profit) : "—",
      hint: "Полученная комиссия минус расходы",
      ...(data
        ? { tone: Number(data.profit) < 0 ? ("negative" as const) : ("positive" as const) }
        : {}),
    },
    {
      label: "Разница потенциальная",
      value: data ? formatMoney(data.potentialProfit) : "—",
      hint: "Если все ожидаемые заявки будут оплачены",
      ...(data
        ? { tone: Number(data.potentialProfit) < 0 ? ("negative" as const) : ("positive" as const) }
        : {}),
    },
  ];

  return (
    <section
      aria-label="Итог платформы за всё время"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      {tiles.map((tile) => (
        <StatTile key={tile.label} {...tile} />
      ))}
    </section>
  );
}

/** The form that puts one cost into the books. */
function RecordExpenseForm({
  organizations,
}: {
  organizations: { value: string; label: string }[];
}): React.JSX.Element {
  const record = useRecordExpense();
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<ExpenseCategory>("INFRASTRUCTURE");
  const [purpose, setPurpose] = useState("");
  const [spentAt, setSpentAt] = useState(today);
  const [organizationId, setOrganizationId] = useState(PLATFORM_ITSELF);
  const [note, setNote] = useState("");

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    record.mutate(
      {
        // Sent as typed: the server reads "1 200,50" as the number it is, and
        // parsing it here would mean two places that decide what a sum looks like.
        amount: amount.trim(),
        category,
        purpose: purpose.trim(),
        spentAt,
        ...(organizationId ? { organizationId } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      },
      {
        onSuccess: (expense) => {
          toast.success(`Расход «${expense.purpose}» записан`);
          setAmount("");
          setPurpose("");
          setNote("");
          // The date and the article stay: expenses are entered in runs, and
          // re-picking "март" and "хостинг" for every line is busywork.
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось записать расход"));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Записать расход</CardTitle>
        <CardDescription>
          Обязательны сумма, дата и пометка за что — по ней потом читается итог. Организацию
          указывайте, если расход понесён ради конкретного клиента: тогда он вычитается из его
          комиссии. Общие расходы платформы (хостинг, реклама, бухгалтерия) оставляйте без
          организации.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
          <Input
            label="Сумма"
            required
            inputMode="decimal"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="1 200,50"
            description="Можно с запятой и пробелами"
          />
          <Input
            label="Дата расхода"
            type="date"
            required
            value={spentAt}
            onChange={(event) => setSpentAt(event.target.value)}
            description="День, которым расход проведён, а не день записи"
          />
          <Select
            label="Статья"
            options={EXPENSE_CATEGORIES.map((value) => ({
              value,
              label: EXPENSE_CATEGORY_LABELS[value],
            }))}
            value={category}
            onValueChange={(value) => setCategory(value as ExpenseCategory)}
          />
          <Select
            label="Организация"
            options={organizations}
            value={organizationId}
            onValueChange={setOrganizationId}
          />
          <Input
            label="За что"
            required
            containerClassName="sm:col-span-2"
            value={purpose}
            onChange={(event) => setPurpose(event.target.value)}
            placeholder="Например: хостинг за март"
          />
          <Textarea
            label="Комментарий"
            containerClassName="sm:col-span-2"
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Номер счёта, подрядчик, любая деталь"
          />
          <div className="sm:col-span-2">
            <Button type="submit" loading={record.isPending}>
              Записать
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

/** One row of the book, with the one destructive action it has. */
function ExpenseRow({ expense }: { expense: PlatformExpense }): React.JSX.Element {
  const remove = useRemoveExpense();
  const amend = useAmendExpense();
  const [armed, setArmed] = useState(false);

  return (
    <tr className="border-border border-b last:border-0">
      <td className="py-3 pr-4 whitespace-nowrap">{formatDay(expense.spentAt)}</td>
      <td className="py-3 pr-4">
        <div className="flex flex-col">
          <span className="font-medium">{expense.purpose}</span>
          {expense.note ? (
            <span className="text-muted-foreground text-xs">{expense.note}</span>
          ) : null}
        </div>
      </td>
      <td className="py-3 pr-4">
        <Badge variant="neutral">{categoryLabel(expense.category)}</Badge>
      </td>
      <td className="py-3 pr-4">
        {expense.organizationId === null ? (
          <span className="text-muted-foreground">Платформа</span>
        ) : (
          <div className="flex flex-col">
            <span>{expense.organizationName ?? "Организация удалена"}</span>
            <button
              type="button"
              className="w-fit text-muted-foreground text-xs underline underline-offset-2 hover:text-foreground"
              disabled={amend.isPending}
              onClick={() => {
                // An explicit null is what moves the cost onto the platform; the
                // hook sends the key, which is how the server tells "carry this
                // yourself" apart from "leave the attribution alone".
                amend.mutate(
                  { id: expense.id, organizationId: null },
                  {
                    onSuccess: () => toast.success("Расход перенесён на платформу"),
                    onError: async (error) => {
                      toast.error(await refusalMessage(error, "Не удалось перенести расход"));
                    },
                  },
                );
              }}
            >
              снять с организации
            </button>
          </div>
        )}
      </td>
      <td className="py-3 pr-4 text-right font-medium tabular-nums">
        {formatMoney(expense.amount)}
      </td>
      <td className="py-3 text-right">
        <Button
          size="sm"
          variant={armed ? "danger" : "ghost"}
          loading={remove.isPending}
          onClick={() => {
            if (!armed) {
              setArmed(true);
              return;
            }
            remove.mutate(expense.id, {
              onSuccess: () => toast.success("Расход убран из книги"),
              onError: async (error) => {
                toast.error(await refusalMessage(error, "Не удалось убрать расход"));
              },
            });
          }}
          onBlur={() => setArmed(false)}
        >
          <Trash2 className="size-4" aria-hidden="true" />
          <span>{armed ? "Точно убрать?" : "Убрать"}</span>
        </Button>
      </td>
    </tr>
  );
}

/**
 * The platform's own books: what it spent, on what, and against whose commission.
 *
 * The bottom line at the top is for the whole platform and for all time; the
 * filters below narrow the ledger and the totals beside it, and nothing else.
 */
export function PlatformFinancePage(): React.JSX.Element {
  const [organizationFilter, setOrganizationFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const organizations = usePlatformOrganizations();
  const ledger = usePlatformExpenses({
    ...(organizationFilter ? { organizationId: organizationFilter } : {}),
    ...(categoryFilter ? { category: categoryFilter } : {}),
    ...(from ? { from } : {}),
    ...(to ? { to } : {}),
  });

  /** For the form: "платформа" first, then every connected organization. */
  const formOrganizations = useMemo(
    () => [
      { value: PLATFORM_ITSELF, label: "Без организации — расход платформы" },
      ...(organizations.data ?? []).map((row) => ({ value: row.id, label: row.name })),
    ],
    [organizations.data],
  );

  /** For the filter: the same list, headed by "all" rather than by a default. */
  const filterOrganizations = useMemo(
    () => [
      { value: "", label: "Все расходы" },
      ...(organizations.data ?? []).map((row) => ({ value: row.id, label: row.name })),
    ],
    [organizations.data],
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Расходы платформы</h1>
        <p className="text-muted-foreground text-sm">
          Что платформа потратила и за что. Ниже — те же деньги против комиссии, которую платят
          организации: разница и показывает, в плюсе платформа или в минусе.
        </p>
      </header>

      <BottomLine />

      <RecordExpenseForm organizations={formOrganizations} />

      <Card>
        <CardHeader>
          <CardTitle>Книга расходов</CardTitle>
          <CardDescription>
            Фильтры сужают и список, и суммы под ним. Период считается по дате расхода, а не по дате
            записи.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Select
              label="Организация"
              options={filterOrganizations}
              value={organizationFilter}
              onValueChange={setOrganizationFilter}
            />
            <Select
              label="Статья"
              options={[
                { value: "", label: "Все статьи" },
                ...EXPENSE_CATEGORIES.map((value) => ({
                  value,
                  label: EXPENSE_CATEGORY_LABELS[value],
                })),
              ]}
              value={categoryFilter}
              onValueChange={setCategoryFilter}
            />
            <Input
              label="С"
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
            />
            <Input
              label="По"
              type="date"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </div>

          {ledger.isLoading ? <LoadingState label="Загрузка расходов" /> : null}

          {ledger.isError ? (
            <Alert variant="danger" title="Не удалось загрузить расходы">
              Проверьте доступ к консоли платформы и повторите попытку.
            </Alert>
          ) : null}

          {ledger.data ? (
            <>
              {ledger.data.truncated ? (
                <Alert variant="warning" title="Показаны не все расходы">
                  Список обрезан, поэтому сумма ниже — только по показанным строкам. Сузьте период.
                </Alert>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="neutral">Всего: {formatMoney(ledger.data.total)}</Badge>
                {ledger.data.byCategory.map((row) => (
                  <Badge key={row.category} variant="neutral">
                    {categoryLabel(row.category)}: {formatMoney(row.amount)} · {row.count}
                  </Badge>
                ))}
              </div>

              {ledger.data.expenses.length === 0 ? (
                <EmptyState
                  icon={<Wallet aria-hidden="true" />}
                  title="Расходов пока нет"
                  description="Запишите первый — он сразу попадёт в разницу наверху."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-3xl text-sm">
                    <thead>
                      <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
                        <th className="py-2 pr-4 font-medium">Дата</th>
                        <th className="py-2 pr-4 font-medium">За что</th>
                        <th className="py-2 pr-4 font-medium">Статья</th>
                        <th className="py-2 pr-4 font-medium">Организация</th>
                        <th className="py-2 pr-4 text-right font-medium">Сумма</th>
                        <th className="py-2 text-right font-medium">Действие</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.data.expenses.map((expense) => (
                        <ExpenseRow key={expense.id} expense={expense} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
