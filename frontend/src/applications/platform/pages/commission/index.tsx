import { Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import {
  type CommissionPayment,
  type OrganizationBreakdown,
  refusalMessage,
  useCommissionPayments,
  usePlatformDashboard,
  usePlatformOrganizations,
  useRecordCommissionPayment,
  useRemoveCommissionPayment,
} from "@/applications/platform/api/platform-api";
import { formatMoney } from "@/applications/platform/lib/billing";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  LoadingState,
  Select,
  Textarea,
  toast,
} from "@/shared/ui";

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
 * Who still owes the platform, for all time.
 *
 * Read off the dashboard rather than off the ledger below, because a debt is the
 * difference between two figures and this screen only holds one of them. Shown
 * unfiltered on purpose: a debt narrowed to March would be March's payments
 * against every month's accrual, which is not a debt at all.
 */
function DebtSummary(): React.JSX.Element {
  const dashboard = usePlatformDashboard("", "");
  const data = dashboard.data;
  const owing = (data?.organizations ?? [])
    .filter((row) => Number(row.commissionDebt) > 0)
    .sort((left, right) => Number(right.commissionDebt) - Number(left.commissionDebt));

  return (
    <div className="flex flex-col gap-4">
      <section
        aria-label="Комиссия за всё время"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
      >
        <StatTile
          label="Начислено"
          value={data ? formatMoney(data.accruedCommission) : "—"}
          hint="По всем засчитанным номерам"
        />
        <StatTile
          label="Поступило"
          value={data ? formatMoney(data.receivedCommission) : "—"}
          hint="Внесено в журнал ниже"
        />
        <StatTile
          label="Долг"
          value={data ? formatMoney(data.commissionDebt) : "—"}
          hint="Начислено минус поступило"
          {...(data
            ? {
                tone:
                  Number(data.commissionDebt) > 0 ? ("negative" as const) : ("positive" as const),
              }
            : {})}
        />
      </section>

      {owing.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Кто должен</CardTitle>
            <CardDescription>
              Организации с непогашенной комиссией, самая большая задолженность сверху. Цифры за всё
              время: долг — это разница между начисленным и поступившим, и период её не сужает.
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-lg text-sm">
              <thead>
                <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
                  <th className="py-2 pr-4 font-medium">Организация</th>
                  <th className="py-2 pr-4 font-medium">Начислено</th>
                  <th className="py-2 pr-4 font-medium">Поступило</th>
                  <th className="py-2 font-medium">Долг</th>
                </tr>
              </thead>
              <tbody>
                {owing.map((row: OrganizationBreakdown) => (
                  <tr
                    className="border-border border-b last:border-0"
                    key={row.organizationId ?? row.name}
                  >
                    <td className="py-3 pr-4 font-medium">{row.name}</td>
                    <td className="py-3 pr-4 tabular-nums">{formatMoney(row.accruedCommission)}</td>
                    <td className="py-3 pr-4 tabular-nums">
                      {formatMoney(row.receivedCommission)}
                    </td>
                    <td className="py-3 font-medium text-destructive tabular-nums">
                      {formatMoney(row.commissionDebt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

/** The form that records one payment as received. */
function RecordPaymentForm({
  organizations,
}: {
  organizations: { value: string; label: string }[];
}): React.JSX.Element {
  const record = useRecordCommissionPayment();
  const [organizationId, setOrganizationId] = useState("");
  const [amount, setAmount] = useState("");
  const [receivedAt, setReceivedAt] = useState(today);
  const [note, setNote] = useState("");

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    record.mutate(
      {
        organizationId,
        // Sent as typed: the server reads "1 200,50" as the number it is, and
        // parsing it here would mean two places that decide what a sum looks like.
        amount: amount.trim(),
        receivedAt,
        ...(note.trim() ? { note: note.trim() } : {}),
      },
      {
        onSuccess: (payment) => {
          toast.success(
            `Поступление ${formatMoney(payment.amount)} от «${payment.organizationName ?? "организации"}» записано`,
          );
          setAmount("");
          setNote("");
          // The payer and the date stay: receipts are entered in runs off one bank
          // statement, and re-picking them for every line is busywork.
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось записать поступление"));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Записать поступление</CardTitle>
        <CardDescription>
          Деньги, которые организатор действительно перевёл платформе. Сумма вычитается из его
          долга: начисление считается автоматически по номерам, а факт оплаты знает только выписка,
          поэтому его вносят руками. Организация обязательна — поступление, которое никому не
          уменьшает долг, учесть негде.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit}>
          <Select
            label="От организации"
            options={organizations}
            value={organizationId}
            onValueChange={setOrganizationId}
          />
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
            label="Дата поступления"
            type="date"
            required
            value={receivedAt}
            onChange={(event) => setReceivedAt(event.target.value)}
            description="День по выписке, а не день записи"
          />
          <Textarea
            label="Комментарий"
            containerClassName="sm:col-span-2"
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Номер платёжного поручения, за какой период"
          />
          <div className="sm:col-span-2">
            <Button type="submit" loading={record.isPending} disabled={!organizationId}>
              Записать
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

/** One row of the ledger, with the one destructive action it has. */
function PaymentRow({ payment }: { payment: CommissionPayment }): React.JSX.Element {
  const remove = useRemoveCommissionPayment();
  const [armed, setArmed] = useState(false);

  return (
    <tr className="border-border border-b last:border-0">
      <td className="py-3 pr-4 whitespace-nowrap">{formatDay(payment.receivedAt)}</td>
      <td className="py-3 pr-4">
        <div className="flex flex-col">
          <span className="font-medium">{payment.organizationName ?? "Организация удалена"}</span>
          {payment.note ? (
            <span className="text-muted-foreground text-xs">{payment.note}</span>
          ) : null}
        </div>
      </td>
      <td className="py-3 pr-4 text-right font-medium tabular-nums">
        {formatMoney(payment.amount)}
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
            remove.mutate(payment.id, {
              onSuccess: () => toast.success("Поступление убрано из журнала"),
              onError: async (error) => {
                toast.error(await refusalMessage(error, "Не удалось убрать поступление"));
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
 * Commission the platform has actually been paid.
 *
 * The debt summary at the top is for the whole platform and for all time; the
 * filters below narrow the journal and the totals beside it, and nothing else.
 */
export function PlatformCommissionPage(): React.JSX.Element {
  const [organizationFilter, setOrganizationFilter] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const organizations = usePlatformOrganizations();
  const ledger = useCommissionPayments({
    ...(organizationFilter ? { organizationId: organizationFilter } : {}),
    ...(from ? { from } : {}),
    ...(to ? { to } : {}),
  });

  /** For the form: no default payer, because guessing one would credit the wrong client. */
  const formOrganizations = useMemo(
    () => [
      { value: "", label: "Выберите организацию" },
      ...(organizations.data ?? []).map((row) => ({ value: row.id, label: row.name })),
    ],
    [organizations.data],
  );

  /** For the filter: the same list, headed by "all" rather than by a default. */
  const filterOrganizations = useMemo(
    () => [
      { value: "", label: "Все организации" },
      ...(organizations.data ?? []).map((row) => ({ value: row.id, label: row.name })),
    ],
    [organizations.data],
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Поступления комиссии</h1>
        <p className="text-muted-foreground text-sm">
          Что организаторы заплатили платформе. Начисление считается само — по номерам, дошедшим до
          конкурса; поступление знает только выписка, поэтому его вносят здесь, и долг закрывается.
        </p>
      </header>

      <DebtSummary />

      <RecordPaymentForm organizations={formOrganizations} />

      <Card>
        <CardHeader>
          <CardTitle>Журнал поступлений</CardTitle>
          <CardDescription>
            Все записанные платежи, свежие сверху. Фильтры сужают и список, и итог рядом с ним:
            период читается по дню, когда деньги пришли, а не по дню записи — так журнал за месяц
            совпадает с актом за тот же месяц.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Select
              label="Организация"
              options={filterOrganizations}
              value={organizationFilter}
              onValueChange={setOrganizationFilter}
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

          {ledger.isLoading ? <LoadingState label="Загрузка поступлений" /> : null}

          {ledger.isError ? (
            <Alert variant="danger" title="Не удалось загрузить поступления">
              Проверьте доступ к консоли платформы и повторите попытку.
            </Alert>
          ) : null}

          {ledger.data ? (
            <>
              <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
                <span className="font-semibold text-xl tabular-nums">
                  {formatMoney(ledger.data.total)}
                </span>
                {ledger.data.byOrganization.map((row) => (
                  <span className="text-muted-foreground text-sm" key={row.organizationId}>
                    {row.organizationName ?? "Организация удалена"} — {formatMoney(row.amount)} (
                    {row.count})
                  </span>
                ))}
              </div>

              {ledger.data.truncated ? (
                <Alert variant="warning" title="Показаны не все поступления">
                  Записей больше, чем помещается на экран, поэтому итог выше считает только
                  показанные. Сузьте период, чтобы увидеть верную сумму.
                </Alert>
              ) : null}

              <div className="overflow-x-auto">
                <table className="w-full min-w-lg text-sm">
                  <thead>
                    <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
                      <th className="py-2 pr-4 font-medium">Дата</th>
                      <th className="py-2 pr-4 font-medium">От кого</th>
                      <th className="py-2 pr-4 text-right font-medium">Сумма</th>
                      <th className="py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {ledger.data.payments.map((payment) => (
                      <PaymentRow key={payment.id} payment={payment} />
                    ))}
                  </tbody>
                </table>
              </div>

              {ledger.data.payments.length === 0 ? (
                <p className="py-6 text-center text-muted-foreground text-sm">
                  По этим фильтрам поступлений нет.
                </p>
              ) : null}
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
