import { useMemo, useState } from "react";

import {
  type OrganizationBreakdown,
  usePlatformDashboard,
} from "@/applications/platform/api/platform-api";
import { formatFeeTier } from "@/applications/platform/lib/billing";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
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

/** Money as a person reads it: grouped thousands, two decimals, no currency lie. */
function money(amount: string): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return amount;
  }
  return `${value.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} BYN`;
}

function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}): React.JSX.Element {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 py-4">
        <span className="text-muted-foreground text-xs uppercase tracking-wide">{label}</span>
        <span className="font-semibold text-2xl">{value}</span>
        {hint ? <span className="text-muted-foreground text-xs">{hint}</span> : null}
      </CardContent>
    </Card>
  );
}

function OrganizationRow({ row }: { row: OrganizationBreakdown }): React.JSX.Element {
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
      <td className="py-3 pr-4 tabular-nums">{money(row.expectedFees)}</td>
      <td className="py-3 pr-4 tabular-nums">{money(row.settledFees)}</td>
      <td className="py-3 pr-4 font-medium tabular-nums">{money(row.expectedCommission)}</td>
      <td className="py-3 tabular-nums">{money(row.settledCommission)}</td>
    </tr>
  );
}

/**
 * The platform operator's summary: how much work sits in each state across every
 * connected organization, the participation fees behind it, and the platform's
 * share of those fees.
 *
 * Two figures per money column on purpose. "Ожидается" is every order that is
 * not a draft or a cancellation — what the festival should collect; "получено"
 * is what has actually been paid. The difference is the operator's follow-up
 * list, and collapsing them into one number would hide it.
 */
export function PlatformDashboardPage(): React.JSX.Element {
  const [organizationId, setOrganizationId] = useState("");
  const [competitionId, setCompetitionId] = useState("");
  const dashboard = usePlatformDashboard(organizationId, competitionId);

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
          Заявки по статусам во всех подключённых организациях, взносы за ними и доля платформы.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
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
      </div>

      <section aria-label="Заявки по статусам" className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {STATUS_LABELS.map(([status, label]) => (
          <StatTile key={status} label={label} value={String(data.statusCounts[status] ?? 0)} />
        ))}
      </section>

      <section aria-label="Деньги" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Взносы ожидаются"
          value={money(data.expectedFees)}
          hint="Все заявки, кроме черновиков и отменённых"
        />
        <StatTile
          label="Взносы получены"
          value={money(data.settledFees)}
          hint="Оплаченные заявки"
        />
        <StatTile
          label="Комиссия ожидается"
          value={money(data.expectedCommission)}
          hint="Доля платформы от ожидаемых взносов"
        />
        <StatTile
          label="Комиссия получена"
          value={money(data.settledCommission)}
          hint="Доля платформы от полученных взносов"
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>По организациям</CardTitle>
          <CardDescription>
            Комиссия считается по условиям организации — процентом от взносов или ценой за каждый
            номер: {STATUS_LABELS.length} статусов сворачиваются в две суммы, ожидаемую и
            полученную.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-3xl text-sm">
            <thead>
              <tr className="border-border border-b text-left text-muted-foreground text-xs uppercase">
                <th className="py-2 pr-4 font-medium">Организация</th>
                <th className="py-2 pr-4 font-medium">Статус</th>
                <th className="py-2 pr-4 font-medium">Условия</th>
                <th className="py-2 pr-4 font-medium">Взносы ожид.</th>
                <th className="py-2 pr-4 font-medium">Взносы получ.</th>
                <th className="py-2 pr-4 font-medium">Комиссия ожид.</th>
                <th className="py-2 font-medium">Комиссия получ.</th>
              </tr>
            </thead>
            <tbody>
              {data.organizations.map((row) => (
                <OrganizationRow key={row.organizationId ?? "unassigned"} row={row} />
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
    </div>
  );
}
