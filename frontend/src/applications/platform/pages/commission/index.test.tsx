/**
 * The receipts ledger — recording a payment, and the debt it closes.
 *
 * Mocked at the hook seam like the sibling console suites, so this is about what
 * the page does with what it is given. Three things are worth pinning down: a sum
 * leaves the page exactly as it was typed (the server is the one place that
 * decides what "1 200,50" means), a payment cannot be submitted without a payer,
 * and the debt beside it is the difference the operator chases.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  CommissionPayment,
  CommissionPaymentLedger,
  OrganizationBreakdown,
  PlatformDashboard,
  PlatformOrganization,
} from "@/applications/platform/api/platform-api";

const record = vi.fn();
const remove = vi.fn();

const PAYMENT: CommissionPayment = {
  id: "payment-1",
  organizationId: "org-1",
  organizationName: "Гармония",
  amount: "70.00",
  receivedAt: "2026-03-20",
  note: "п/п 114",
  createdAt: "2026-03-20T10:00:00Z",
  updatedAt: "2026-03-20T10:00:00Z",
};

const LEDGER: CommissionPaymentLedger = {
  payments: [PAYMENT],
  total: "70.00",
  byOrganization: [
    { organizationId: "org-1", organizationName: "Гармония", amount: "70.00", count: 1 },
  ],
  truncated: false,
};

const BREAKDOWN: OrganizationBreakdown = {
  organizationId: "org-1",
  name: "Гармония",
  status: "ACTIVE",
  billingModel: "COMMISSION_PERCENT",
  commissionPercent: "10.00",
  feeTiers: [],
  competitions: 1,
  applications: 4,
  statusCounts: {},
  orderFees: "1000.00",
  performances: 10,
  participants: 24,
  commissionBase: "1000.00",
  accruedCommission: "100.00",
  receivedCommission: "70.00",
  commissionDebt: "30.00",
  feeBreakdown: [],
  expenses: "0.00",
  profit: "70.00",
};

const DASHBOARD: PlatformDashboard = {
  statusCounts: {},
  applications: 4,
  orderFees: "1000.00",
  performances: 10,
  participants: 24,
  commissionBase: "1000.00",
  accruedCommission: "100.00",
  receivedCommission: "70.00",
  commissionDebt: "30.00",
  expenses: "0.00",
  unattributedExpenses: "0.00",
  profit: "70.00",
  expensesApply: true,
  periodApplies: false,
  organizations: [BREAKDOWN],
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

const ledger = {
  data: LEDGER as CommissionPaymentLedger | undefined,
  isLoading: false,
  isError: false,
};
const dashboard = { data: DASHBOARD as PlatformDashboard | undefined };

vi.mock("@/applications/platform/api/platform-api", async () => {
  const actual = await vi.importActual<typeof import("@/applications/platform/api/platform-api")>(
    "@/applications/platform/api/platform-api",
  );
  return {
    ...actual,
    useCommissionPayments: () => ledger,
    usePlatformDashboard: () => dashboard,
    usePlatformOrganizations: () => ({ data: [ORGANIZATION], isLoading: false, isError: false }),
    useRecordCommissionPayment: () => ({ mutate: record, isPending: false }),
    useRemoveCommissionPayment: () => ({ mutate: remove, isPending: false }),
    refusalMessage: async (_error: unknown, fallback: string) => fallback,
  };
});

const { PlatformCommissionPage } = await import("./index");

// jsdom implements neither, and the Radix select the payer picker is built on
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
  remove.mockClear();
  ledger.data = LEDGER;
  ledger.isError = false;
  dashboard.data = DASHBOARD;
});

describe("PlatformCommissionPage — what is still owed", () => {
  it("prints accrued, received and the difference", () => {
    const summary = () => screen.getByRole("region", { name: "Комиссия за всё время" });
    render(<PlatformCommissionPage />);

    expect(within(summary()).getByText("100,00 BYN")).toBeInTheDocument();
    expect(within(summary()).getByText("70,00 BYN")).toBeInTheDocument();
    expect(within(summary()).getByText("30,00 BYN")).toBeInTheDocument();
  });

  it("lists the organizations that still owe something", () => {
    render(<PlatformCommissionPage />);

    expect(screen.getByText("Кто должен")).toBeInTheDocument();
  });

  it("says nothing rather than listing a debtor when everybody has paid", () => {
    // Zero debt is not a row worth printing, and an empty table reads as a bug.
    dashboard.data = {
      ...DASHBOARD,
      commissionDebt: "0.00",
      organizations: [{ ...BREAKDOWN, receivedCommission: "100.00", commissionDebt: "0.00" }],
    };

    render(<PlatformCommissionPage />);

    expect(screen.queryByText("Кто должен")).not.toBeInTheDocument();
  });
});

describe("PlatformCommissionPage — recording a payment", () => {
  it("sends the sum exactly as it was typed", async () => {
    // The server is the one place that decides what "1 200,50" means; parsing it
    // here would be a second opinion that can disagree.
    render(<PlatformCommissionPage />);

    await pick(0, "Гармония");
    await userEvent.type(screen.getByLabelText(/Сумма/), "1 200,50");
    await userEvent.click(screen.getByRole("button", { name: "Записать" }));

    expect(record).toHaveBeenCalledTimes(1);
    expect(record.mock.calls[0]?.[0]).toMatchObject({
      organizationId: "org-1",
      amount: "1 200,50",
    });
  });

  it("carries no note at all rather than an empty one", () => {
    render(<PlatformCommissionPage />);

    expect(screen.getByLabelText(/Комментарий/)).toHaveValue("");
  });

  it("refuses to submit until a payer is chosen", () => {
    // A payment that reduces nobody's debt has nowhere to go, so the button is
    // held rather than letting the server refuse what the form could have.
    render(<PlatformCommissionPage />);

    expect(screen.getByRole("button", { name: "Записать" })).toBeDisabled();
  });
});

describe("PlatformCommissionPage — the journal", () => {
  it("shows the payer, the day and the note", () => {
    render(<PlatformCommissionPage />);

    expect(screen.getByText("20 марта 2026 г.")).toBeInTheDocument();
    expect(screen.getByText("п/п 114")).toBeInTheDocument();
  });

  it("asks before striking a payment out", async () => {
    render(<PlatformCommissionPage />);

    await userEvent.click(screen.getByRole("button", { name: /Убрать/ }));

    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Точно убрать\?/ })).toBeInTheDocument();
  });

  it("strikes it out on the second press", async () => {
    render(<PlatformCommissionPage />);

    await userEvent.click(screen.getByRole("button", { name: /Убрать/ }));
    await userEvent.click(screen.getByRole("button", { name: /Точно убрать\?/ }));

    expect(remove).toHaveBeenCalledWith("payment-1", expect.anything());
  });

  it("says the total is partial when the list was cut short", () => {
    ledger.data = { ...LEDGER, truncated: true };

    render(<PlatformCommissionPage />);

    expect(screen.getByText("Показаны не все поступления")).toBeInTheDocument();
  });

  it("says so plainly when nothing matches the filters", () => {
    ledger.data = { payments: [], total: "0.00", byOrganization: [], truncated: false };

    render(<PlatformCommissionPage />);

    expect(screen.getByText("По этим фильтрам поступлений нет.")).toBeInTheDocument();
  });
});
