/**
 * The operator's expense book — entering a cost, and the bottom line above it.
 *
 * Mocked at the hook seam like the sibling console suites, so this is about what the
 * page does with what it is given. Three things are worth pinning down: a sum leaves
 * the page exactly as it was typed (the server is the one place that decides what
 * "1 200,50" means), a cost with no organization chosen carries no `organizationId`
 * at all rather than an empty one, and a loss is printed as a loss.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExpenseLedger,
  PlatformDashboard,
  PlatformExpense,
  PlatformOrganization,
} from "@/applications/platform/api/platform-api";

const record = vi.fn();
const amend = vi.fn();
const remove = vi.fn();

const EXPENSE: PlatformExpense = {
  id: "expense-1",
  amount: "400.00",
  category: "INFRASTRUCTURE",
  purpose: "Хостинг за март",
  spentAt: "2026-03-01",
  note: "",
  organizationId: null,
  organizationName: null,
  createdAt: "2026-03-01T10:00:00Z",
  updatedAt: "2026-03-01T10:00:00Z",
};

const LEDGER: ExpenseLedger = {
  expenses: [EXPENSE],
  total: "400.00",
  byCategory: [{ category: "INFRASTRUCTURE", amount: "400.00", count: 1 }],
  truncated: false,
};

const DASHBOARD: PlatformDashboard = {
  statusCounts: {},
  applications: 0,
  orderFees: "1000.00",
  performances: 10,
  participants: 24,
  commissionBase: "1000.00",
  accruedCommission: "100.00",
  receivedCommission: "70.00",
  commissionDebt: "30.00",
  expenses: "400.00",
  unattributedExpenses: "400.00",
  profit: "-330.00",
  expensesApply: true,
  periodApplies: false,
  organizations: [],
  competitions: [],
};

const ORGANIZATION: PlatformOrganization = {
  id: "org-1",
  name: "Гармония",
  slug: "garmoniya",
  status: "ACTIVE",
  billingModel: "COMMISSION_PERCENT",
  commissionPercent: "10.00",
  feeTiers: [],
  createdAt: "2026-01-01T00:00:00Z",
};

const ledger = { data: LEDGER as ExpenseLedger | undefined, isLoading: false, isError: false };
const dashboard = { data: DASHBOARD as PlatformDashboard | undefined };

vi.mock("@/applications/platform/api/platform-api", async () => {
  const actual = await vi.importActual<typeof import("@/applications/platform/api/platform-api")>(
    "@/applications/platform/api/platform-api",
  );
  return {
    EXPENSE_CATEGORIES: actual.EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS: actual.EXPENSE_CATEGORY_LABELS,
    usePlatformExpenses: () => ledger,
    usePlatformDashboard: () => dashboard,
    usePlatformOrganizations: () => ({ data: [ORGANIZATION], isLoading: false, isError: false }),
    useRecordExpense: () => ({ mutate: record, isPending: false }),
    useAmendExpense: () => ({ mutate: amend, isPending: false }),
    useRemoveExpense: () => ({ mutate: remove, isPending: false }),
    refusalMessage: async (_error: unknown, fallback: string) => fallback,
  };
});

const { PlatformFinancePage } = await import("./index");

// jsdom implements neither, and the Radix select the article picker is built on
// calls both while opening (the same stubs the Select suite installs).
Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

/** Pick an option in one of the page's selects, named by its visible label. */
async function pick(index: number, option: string): Promise<void> {
  const triggers = screen.getAllByRole("combobox");
  await userEvent.click(triggers[index] as HTMLElement);
  await userEvent.click(await screen.findByRole("option", { name: option }));
}

beforeEach(() => {
  record.mockClear();
  amend.mockClear();
  remove.mockClear();
  ledger.data = LEDGER;
  ledger.isError = false;
  dashboard.data = DASHBOARD;
});

describe("PlatformFinancePage — the bottom line", () => {
  it("prints the difference between the commission received and the costs", () => {
    render(<PlatformFinancePage />);

    const summary = screen.getByRole("region", { name: "Итог платформы за всё время" });

    expect(within(summary).getByText("70,00 BYN")).toBeInTheDocument();
    expect(within(summary).getByText("400,00 BYN")).toBeInTheDocument();
    expect(within(summary).getByText("-330,00 BYN")).toBeInTheDocument();
  });

  it("reports what is still owed as a debt rather than folding it into the profit", () => {
    // 100.00 accrued against 70.00 received. The missing 30.00 is a collection
    // problem, not income — a profit figure that counted it would be reporting
    // money the platform does not have.
    render(<PlatformFinancePage />);

    const summary = screen.getByRole("region", { name: "Итог платформы за всё время" });

    expect(within(summary).getByText("Долг организаторов")).toBeInTheDocument();
    expect(within(summary).getByText("30,00 BYN")).toBeInTheDocument();
  });

  it("marks a loss rather than printing it like any other figure", () => {
    render(<PlatformFinancePage />);

    const summary = screen.getByRole("region", { name: "Итог платформы за всё время" });

    expect(within(summary).getByText("-330,00 BYN").className).toContain("text-destructive");
  });

  it("shows an em dash rather than a zero while the summary is still loading", () => {
    dashboard.data = undefined;

    render(<PlatformFinancePage />);

    const summary = screen.getByRole("region", { name: "Итог платформы за всё время" });
    // A profit of zero and a profit not yet known are different facts.
    expect(within(summary).getAllByText("—").length).toBeGreaterThan(0);
  });
});

describe("PlatformFinancePage — recording a cost", () => {
  it("sends the sum exactly as it was typed", async () => {
    render(<PlatformFinancePage />);

    await userEvent.type(screen.getByLabelText(/Сумма/), "1 200,50");
    await userEvent.type(screen.getByLabelText(/За что/), "Хостинг за март");
    await userEvent.click(screen.getByRole("button", { name: "Записать" }));

    expect(record).toHaveBeenCalledTimes(1);
    // Parsing it here would mean two places deciding what a sum looks like, and
    // the server is already one of them.
    expect(record.mock.calls[0]?.[0]).toMatchObject({
      amount: "1 200,50",
      purpose: "Хостинг за март",
      category: "INFRASTRUCTURE",
    });
  });

  it("carries no organization at all when the cost is the platform's own", async () => {
    render(<PlatformFinancePage />);

    await userEvent.type(screen.getByLabelText(/Сумма/), "400");
    await userEvent.type(screen.getByLabelText(/За что/), "Сервер");
    await userEvent.click(screen.getByRole("button", { name: "Записать" }));

    expect(record.mock.calls[0]?.[0]).not.toHaveProperty("organizationId");
  });

  it("names the organization when the cost was carried for one", async () => {
    render(<PlatformFinancePage />);

    await userEvent.type(screen.getByLabelText(/Сумма/), "50");
    await userEvent.type(screen.getByLabelText(/За что/), "Печать дипломов");
    // Second select on the form: the article is first, the organization follows.
    await pick(1, "Гармония");
    await userEvent.click(screen.getByRole("button", { name: "Записать" }));

    expect(record.mock.calls[0]?.[0]).toMatchObject({ organizationId: "org-1" });
  });
});

describe("PlatformFinancePage — the ledger", () => {
  it("totals the rows in scope and names the articles behind them", () => {
    render(<PlatformFinancePage />);

    expect(screen.getByText("Всего: 400,00 BYN")).toBeInTheDocument();
    expect(screen.getByText(/Хостинг и инфраструктура: 400,00 BYN/)).toBeInTheDocument();
  });

  it("asks before striking a cost out", async () => {
    render(<PlatformFinancePage />);

    await userEvent.click(screen.getByRole("button", { name: /Убрать/ }));

    expect(remove).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /Точно убрать/ }));
    expect(remove).toHaveBeenCalledWith("expense-1", expect.anything());
  });
});
