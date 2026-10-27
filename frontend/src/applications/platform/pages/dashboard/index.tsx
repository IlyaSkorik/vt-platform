import { useMemo, useState } from "react";

import {
  type OrganizationBreakdown,
  type PlatformAudience,
  usePlatformAudience,
  usePlatformDashboard,
} from "@/applications/platform/api/platform-api";
import { formatFeeTier, formatMoney, formatTierRange } from "@/applications/platform/lib/billing";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  LoadingState,
  Select,
} from "@/shared/ui";

/** The funnel, in the order work actually moves through it. */
const STATUS_LABELS: Array<[string, string]> = [
  ["DRAFT", "Черновики"],
  ["SUBMITTED", "Поданы"],
  ["WAITING_PAYMENT", "Ждут оплаты"],
  ["PAID", "Оплачены"],
  ["COMPLETED", "Завершены"],
  ["CANCELLED", "Отменены"],
];

/** A head count as a person reads it: grouped thousands, no decimals. */
function count(value: number): string {
  return value.toLocaleString("ru-RU");
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
  /** Colours the figure. Used only where a minus sign is the news, not decoration. */
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

/** Below zero is the one figure on this screen that has to be unmissable. */
function profitTone(amount: string): "positive" | "negative" {
  return Number(amount) < 0 ? "negative" : "positive";
}

/**
 * Who is on the platform, as opposed to how much work is on it.
 *
 * Sits above the filters because nothing below them applies to it: these are counts
 * of people, and a person does not belong to one festival. Kept on its own query so
 * a failure here leaves the funnel and the money on screen — an em dash says "not
 * loaded" without pretending the platform has nobody.
 */
function AudienceSection({
  audience,
}: {
  audience: PlatformAudience | undefined;
}): React.JSX.Element {
  const tiles: Array<{
    label: string;
    total: number | undefined;
    subset: string;
    of: number | undefined;
  }> = [
    {
      label: "Личные кабинеты",
      total: audience?.cabinets.total,
      subset: "с подтверждённой почтой",
      of: audience?.cabinets.emailVerified,
    },
    {
      label: "Участники в реестре",
      total: audience?.participants.total,
      subset: "в архиве",
      of: audience?.participants.archived,
    },
    {
      label: "Педагоги",
      total: audience?.teachers.total,
      subset: "в архиве",
      of: audience?.teachers.archived,
    },
  ];

  return (
    <section aria-label="Кто на платформе" className="grid gap-3 sm:grid-cols-3">
      {tiles.map((tile) => (
        <StatTile
          key={tile.label}
          label={tile.label}
          value={tile.total == null ? "—" : count(tile.total)}
          {...(tile.of == null ? {} : { hint: `${count(tile.of)} ${tile.subset}` })}
        />
      ))}
    </section>
  );
}

function OrganizationRow({
  row,
  withProfit,
}: {
  row: OrganizationBreakdown;
  /** False under a competition filter, where the expense columns mean nothing. */
  withProfit: boolean;
}): React.JSX.Element {
  return (
    <tr className="border-border border-b last:border-0">
      <td className="py-3 pr-4">
        <div className="flex flex-col">
          <span className="font-medium">{row.name}</span>
          <span className="text-muted-foreground text-xs">
            {row.competitions} фестивалей · {row.applications} заявок
          </span>
        </div>
      </td>
      <td className="py-3 pr-4">
        <Badge variant={row.status === "ACTIVE" ? "success" : "warning"}>
          {row.status === "ACTIVE" ? "Активна" : "Приостановлена"}
        </Badge>
      </td>
      <td className="py-3 pr-4">
        {row.billingModel === "PER_PERFORMANCE_FEE" ? (
          <div className="flex flex-col">
            <span>Цена за номер</span>
            <span className="text-muted-foreground text-xs">
              {row.feeTiers.map(formatFeeTier).join(" · ")}
            </span>
          </div>
        ) : (
          <span className="tabular-nums">{row.commissionPercent}%</span>
        )}
      </td>
      <td className="py-3 pr-4 tabular-nums">
        <div className="flex flex-col">
          <span>{count(row.performances)}</span>
          <span className="text-muted-foreground text-xs">
            {count(row.participants)} участников
          </span>
        </div>
      </td>
      <td className="py-3 pr-4 font-medium tabular-nums">{formatMoney(row.accruedCommission)}</td>
      <td className="py-3 pr-4 tabular-nums">{formatMoney(row.receivedCommission)}</td>
      <td
        className={
          Number(row.commissionDebt) > 0
            ? "py-3 pr-4 font-medium text-destructive tabular-nums"
            : "py-3 pr-4 tabular-nums"
        }
      >
        {formatMoney(row.commissionDebt)}
      </td>
      {withProfit ? (
        <>
          <td className="py-3 pr-4 tabular-nums">{formatMoney(row.expenses)}</td>
          <td
            className={
              Number(row.profit) < 0
                ? "py-3 font-medium text-destructive tabular-nums"
                : "py-3 font-medium tabular-nums"
            }
          >
            {formatMoney(row.profit)}
          </td>
        </>
      ) : null}
    </tr>
  );
}

/**
 * The per-band table an act is written from.
 *
 * Only the per-performance model has one: under a percentage there are no bands,
 * and an empty table would imply the organization is billed off a price list it
 * is not. Rendered under the organization's own name because an act is written
 * for one client at a time.
 */
function FeeBreakdownCard({ row }: { row: OrganizationBreakdown }): React.JSX.Element | null {
  if (row.feeBreakdown.length === 0) {
    return null;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Разбивка по тарифу — {row.name}</CardTitle>
        <CardDescription>
          Сколько номеров какого размера засчитано и по какой цене. Строки складываются в
          начисленную комиссию: {formatMoney(row.accruedCommission)}. Диапазоны, в которые ничего не
          попало, показаны нулями — так таблицу можно сверить с прайсом организатора.
        </CardDescription>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-lg text-sm">
          <thead>
            <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
              <th className="py-2 pr-4 font-medium">Участников в номере</th>
              <th className="py-2 pr-4 font-medium">Номеров</th>
              <th className="py-2 pr-4 font-medium">Цена за номер</th>
              <th className="py-2 font-medium">Сумма</th>
            </tr>
          </thead>
          <tbody>
            {row.feeBreakdown.map((tier) => (
              <tr className="border-border border-b last:border-0" key={tier.rangeLabel}>
                <td className="py-3 pr-4">
                  {formatTierRange(tier.minParticipants, tier.maxParticipants)}
                </td>
                <td className="py-3 pr-4 tabular-nums">{count(tier.performances)}</td>
                <td className="py-3 pr-4 tabular-nums">{formatMoney(tier.unitAmount)}</td>
                <td className="py-3 font-medium tabular-nums">{formatMoney(tier.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-border border-t-2">
              <td className="py-3 pr-4 font-medium">Итого</td>
              <td className="py-3 pr-4 font-medium tabular-nums">{count(row.performances)}</td>
              <td className="py-3 pr-4" />
              <td className="py-3 font-medium tabular-nums">
                {formatMoney(row.accruedCommission)}
              </td>
            </tr>
          </tfoot>
        </table>
      </CardContent>
    </Card>
  );
}

/**
 * The platform operator's summary: who is registered on the platform, how much work
 * sits in each state across every connected organization, and the three money
 * figures the screen exists for — what the platform is owed, what it has been paid,
 * and the difference.
 *
 * Commission is counted per номер, not per заявка. An order is a basket: it can
 * hold five entries, be half cancelled, and carry services the organizer sells and
 * the platform has no share of. So the figures below are built from entries that
 * are actually taking part, priced either off the organization's tariff or as a
 * percentage of what those entries cost.
 */
export function PlatformDashboardPage(): React.JSX.Element {
  const [organizationId, setOrganizationId] = useState("");
  const [competitionId, setCompetitionId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const dashboard = usePlatformDashboard(organizationId, competitionId, from, to);
  const audience = usePlatformAudience();

  const organizationOptions = useMemo(
    () => [
      { value: "", label: "Все организации" },
      ...(dashboard.data?.organizations ?? [])
        .filter((row) => row.organizationId != null)
        .map((row) => ({ value: row.organizationId as string, label: row.name })),
    ],
    [dashboard.data],
  );

  const competitionOptions = useMemo(
    () => [
      { value: "", label: "Все фестивали" },
      ...(dashboard.data?.competitions ?? []).map((option) => ({
        value: option.id,
        label: `${option.title} — ${option.organizationName}`,
      })),
    ],
    [dashboard.data],
  );

  if (dashboard.isLoading) {
    return <LoadingState label="Загрузка сводки платформы" />;
  }

  if (dashboard.isError || dashboard.data == null) {
    return (
      <EmptyState
        title="Не удалось загрузить сводку"
        description="Проверьте доступ к консоли платформы и повторите попытку."
      />
    );
  }

  const data = dashboard.data;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Сводка платформы</h1>
        <p className="text-muted-foreground text-sm">
          Кто зарегистрирован на платформе, заявки по статусам во всех подключённых организациях и
          деньги за ними: сколько начислено, сколько поступило и сколько ещё должны.
        </p>
      </header>

      <AudienceSection audience={audience.data} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Select
          label="Организация"
          options={organizationOptions}
          value={organizationId}
          onValueChange={(value) => {
            setOrganizationId(value);
            setCompetitionId("");
          }}
        />
        <Select
          label="Фестиваль"
          options={competitionOptions}
          value={competitionId}
          onValueChange={setCompetitionId}
        />
        <Input
          label="Период с"
          type="date"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
        />
        <Input
          label="Период по"
          type="date"
          value={to}
          onChange={(event) => setTo(event.target.value)}
        />
      </div>

      <section aria-label="Заявки по статусам" className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {STATUS_LABELS.map(([status, label]) => (
          <StatTile key={status} label={label} value={String(data.statusCounts[status] ?? 0)} />
        ))}
      </section>

      {/* A period filters the money and not the funnel: an order spans the weeks
          between being drafted and being paid, so there is no one date to file it
          under. Said out loud rather than left to look like the dates applied. */}
      {data.periodApplies ? (
        <p className="text-muted-foreground text-sm">
          Заявки по статусам показаны за всё время — у заявки нет одной даты, по которой её можно
          отнести к периоду. Период применён к деньгам ниже.
        </p>
      ) : null}

      <section aria-label="Комиссия" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Номеров засчитано"
          value={count(data.performances)}
          hint={`${count(data.participants)} участников в них`}
        />
        <StatTile
          label="Комиссия начислена"
          value={formatMoney(data.accruedCommission)}
          hint="По условиям каждой организации"
        />
        <StatTile
          label="Комиссия поступила"
          value={formatMoney(data.receivedCommission)}
          hint="Внесено вручную по факту оплаты"
        />
        <StatTile
          label="Долг организаторов"
          value={formatMoney(data.commissionDebt)}
          hint="Начислено минус поступило"
          tone={Number(data.commissionDebt) > 0 ? "negative" : "positive"}
        />
      </section>

      {/* The bottom line. Hidden under a competition filter rather than shown as a
          zero: expenses and receipts are recorded per organization and never per
          festival, so there is nothing honest to subtract for one festival. */}
      {data.expensesApply ? (
        <section aria-label="Прибыль" className="grid gap-3 sm:grid-cols-2">
          <StatTile
            label="Расходы"
            value={formatMoney(data.expenses)}
            hint={`${formatMoney(data.unattributedExpenses)} — общие, без организации`}
          />
          <StatTile
            label="Разница"
            value={formatMoney(data.profit)}
            hint="Поступившая комиссия минус расходы"
            tone={profitTone(data.profit)}
          />
        </section>
      ) : (
        <p className="text-muted-foreground text-sm">
          Расходы и поступления записываются по организациям, а не по фестивалям, поэтому при
          выбранном фестивале прибыль не считается. Снимите фильтр по фестивалю, чтобы увидеть
          разницу.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>По организациям</CardTitle>
          <CardDescription>
            Комиссия начисляется за каждый номер, дошедший до конкурса, — процентом от его взноса
            или ценой по тарифу организации. «Поступило» — это то, что оператор внёс в журнал
            поступлений по факту оплаты; долг — разница между начисленным и поступившим. Разница в
            последней колонке — поступившая комиссия минус расходы, записанные на эту организацию;
            общие расходы платформы в строки не входят и учтены только в итоге выше.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-3xl text-sm">
            <thead>
              <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
                <th className="py-2 pr-4 font-medium">Организация</th>
                <th className="py-2 pr-4 font-medium">Статус</th>
                <th className="py-2 pr-4 font-medium">Условия</th>
                <th className="py-2 pr-4 font-medium">Номеров</th>
                <th className="py-2 pr-4 font-medium">Начислено</th>
                <th className="py-2 pr-4 font-medium">Поступило</th>
                <th className="py-2 pr-4 font-medium">Долг</th>
                {data.expensesApply ? (
                  <>
                    <th className="py-2 pr-4 font-medium">Расходы</th>
                    <th className="py-2 font-medium">Разница</th>
                  </>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {data.organizations.map((row) => (
                <OrganizationRow
                  key={row.organizationId ?? "unassigned"}
                  row={row}
                  withProfit={data.expensesApply}
                />
              ))}
            </tbody>
          </table>
          {data.organizations.length === 0 ? (
            <p className="py-6 text-center text-muted-foreground text-sm">
              Пока не подключено ни одной организации.
            </p>
          ) : null}
        </CardContent>
      </Card>

      {data.organizations.map((row) => (
        <FeeBreakdownCard key={row.organizationId ?? "unassigned"} row={row} />
      ))}
    </div>
  );
}
