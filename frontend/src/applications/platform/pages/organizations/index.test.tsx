/**
 * The organizations page — the console where the operator sets the terms.
 *
 * The API layer is mocked rather than the network, like the test-bench suite next
 * door: stubbing at the hook seam keeps this about the page. What is worth pinning
 * down here is the tariff editor — the operator only ever types each band's upper
 * bound, and the payload that leaves the page must carry the derived lower bounds,
 * because that derivation is what makes a gap or an overlap impossible.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlatformOrganization } from "@/applications/platform/api/platform-api";

const connect = vi.fn();
const update = vi.fn();
const organizations = {
  data: [] as PlatformOrganization[],
  isLoading: false,
  isError: false,
};

vi.mock("@/applications/platform/api/platform-api", () => ({
  usePlatformOrganizations: () => organizations,
  useConnectOrganization: () => ({ mutate: connect, isPending: false }),
  useUpdateOrganization: () => ({ mutate: update, isPending: false }),
  refusalMessage: async (_error: unknown, fallback: string) => fallback,
}));

const { PlatformOrganizationsPage } = await import("./index");

// jsdom implements neither, and the Radix select the model picker is built on calls
// both while opening (the same stubs the Select suite installs).
Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

const PERCENT_ORGANIZATION: PlatformOrganization = {
  id: "org-1",
  name: "Гармония",
  slug: "garmoniya",
  status: "ACTIVE",
  billingModel: "COMMISSION_PERCENT",
  commissionPercent: "7.00",
  feeTiers: [],
  createdAt: "2026-08-01T09:00:00Z",
};

const FEE_ORGANIZATION: PlatformOrganization = {
  ...PERCENT_ORGANIZATION,
  id: "org-2",
  name: "Тарифный дом",
  slug: "tarifnyy-dom",
  billingModel: "PER_PERFORMANCE_FEE",
  feeTiers: [
    { minParticipants: 1, maxParticipants: 1, amount: "2.50" },
    { minParticipants: 2, maxParticipants: 5, amount: "4.00" },
    { minParticipants: 6, maxParticipants: null, amount: "6.00" },
  ],
};

/**
 * Pick a billing model on the ``which`` picker: the connect form owns the first one,
 * each organization card the ones after it.
 */
async function pickBillingModel(which: "form" | "card", label: string): Promise<void> {
  const triggers = screen.getAllByRole("combobox");
  const trigger = which === "form" ? triggers[0] : triggers.at(-1);
  await userEvent.click(trigger as HTMLElement);
  await userEvent.click(await screen.findByRole("option", { name: label }));
}

beforeEach(() => {
  connect.mockClear();
  update.mockClear();
  organizations.data = [];
  organizations.isLoading = false;
  organizations.isError = false;
});

describe("connecting an organization", () => {
  it("sends the percentage terms by default", async () => {
    render(<PlatformOrganizationsPage />);

    await userEvent.type(screen.getByLabelText(/Название/), "Гармония");
    await userEvent.type(screen.getByLabelText(/Почта владельца/), "director@example.com");
    await userEvent.clear(screen.getByLabelText(/Комиссия платформы/));
    await userEvent.type(screen.getByLabelText(/Комиссия платформы/), "12.5");
    await userEvent.click(screen.getByRole("button", { name: /Подключить и отправить/ }));

    expect(connect).toHaveBeenCalledTimes(1);
    expect(connect.mock.calls[0]?.[0]).toMatchObject({
      name: "Гармония",
      ownerEmail: "director@example.com",
      billingModel: "COMMISSION_PERCENT",
      commissionPercent: "12.5",
    });
  });

  it("sends a tariff grid with the lower bounds derived from the row above", async () => {
    render(<PlatformOrganizationsPage />);

    await userEvent.type(screen.getByLabelText(/Название/), "Тарифный дом");
    await userEvent.type(screen.getByLabelText(/Почта владельца/), "tariff@example.com");
    await pickBillingModel("form", "Фиксированная цена за номер");

    // Two closed bands above the open-ended one: "1" and "2–5", then "6+".
    await userEvent.click(screen.getByRole("button", { name: /Добавить правило/ }));
    await userEvent.click(screen.getByRole("button", { name: /Добавить правило/ }));
    const bounds = screen.getAllByLabelText(/Верхняя граница правила/);
    const prices = screen.getAllByLabelText(/Стоимость правила/);
    await userEvent.clear(bounds[0] as HTMLElement);
    await userEvent.type(bounds[0] as HTMLElement, "1");
    await userEvent.clear(bounds[1] as HTMLElement);
    await userEvent.type(bounds[1] as HTMLElement, "5");
    await userEvent.type(prices[0] as HTMLElement, "2.50");
    await userEvent.type(prices[1] as HTMLElement, "4");
    await userEvent.type(prices[2] as HTMLElement, "6");

    await userEvent.click(screen.getByRole("button", { name: /Подключить и отправить/ }));

    expect(connect.mock.calls[0]?.[0]).toMatchObject({
      billingModel: "PER_PERFORMANCE_FEE",
      feeTiers: [
        { minParticipants: 1, maxParticipants: 1, amount: "2.50" },
        { minParticipants: 2, maxParticipants: 5, amount: "4.00" },
        { minParticipants: 6, maxParticipants: null, amount: "6.00" },
      ],
    });
  });

  it("refuses to submit a tariff grid with a price missing", async () => {
    render(<PlatformOrganizationsPage />);

    await userEvent.type(screen.getByLabelText(/Название/), "Тарифный дом");
    await userEvent.type(screen.getByLabelText(/Почта владельца/), "tariff@example.com");
    await pickBillingModel("form", "Фиксированная цена за номер");
    await userEvent.click(screen.getByRole("button", { name: /Подключить и отправить/ }));

    expect(connect).not.toHaveBeenCalled();
    expect(screen.getByText("Цена вида 2.50")).toBeInTheDocument();
  });
});

describe("an organization's terms", () => {
  it("shows the terms it runs on today", () => {
    organizations.data = [FEE_ORGANIZATION];

    render(<PlatformOrganizationsPage />);

    expect(screen.getByText(/Цена за номер/)).toBeInTheDocument();
    expect(screen.getByDisplayValue("2.50")).toBeInTheDocument();
  });

  it("saves a new rate for an organization billed a percentage", async () => {
    organizations.data = [PERCENT_ORGANIZATION];

    render(<PlatformOrganizationsPage />);
    const rate = screen.getByLabelText("Комиссия, %");
    await userEvent.clear(rate);
    await userEvent.type(rate, "9");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить ставку" }));

    expect(update).toHaveBeenCalledWith(
      { id: "org-1", billingModel: "COMMISSION_PERCENT", commissionPercent: "9" },
      expect.anything(),
    );
  });

  it("switches an organization onto the tariff grid", async () => {
    organizations.data = [PERCENT_ORGANIZATION];

    render(<PlatformOrganizationsPage />);
    await pickBillingModel("card", "Фиксированная цена за номер");
    await userEvent.type(screen.getByLabelText(/Стоимость правила 1/), "3");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить тарифы" }));

    expect(update).toHaveBeenCalledWith(
      {
        id: "org-1",
        billingModel: "PER_PERFORMANCE_FEE",
        feeTiers: [{ minParticipants: 1, maxParticipants: null, amount: "3.00" }],
      },
      expect.anything(),
    );
  });

  it("keeps the save button quiet while nothing has changed", () => {
    organizations.data = [FEE_ORGANIZATION];

    render(<PlatformOrganizationsPage />);

    expect(screen.getByRole("button", { name: "Сохранить тарифы" })).toBeDisabled();
  });
});
