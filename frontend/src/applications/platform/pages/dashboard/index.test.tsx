/**
 * The operator's summary page — the audience tiles above the funnel.
 *
 * Mocked at the hook seam like the sibling console suites, so this is about what the
 * page prints. Two things worth pinning down: the head counts are read separately
 * from the dashboard (a failure there must not blank the page), and the archived /
 * unconfirmed subsets are reported beside each total rather than subtracted from it.
 */
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlatformAudience, PlatformDashboard } from "@/applications/platform/api/platform-api";

const DASHBOARD: PlatformDashboard = {
  statusCounts: { DRAFT: 1, SUBMITTED: 2, WAITING_PAYMENT: 0, PAID: 3, COMPLETED: 0, CANCELLED: 0 },
  applications: 6,
  expectedFees: "500.00",
  settledFees: "300.00",
  expectedCommission: "50.00",
  settledCommission: "30.00",
  organizations: [],
  competitions: [],
};

const AUDIENCE: PlatformAudience = {
  cabinets: { total: 1284, emailVerified: 902 },
  participants: { total: 3407, archived: 112 },
  teachers: { total: 208, archived: 7 },
};

const dashboard = {
  data: DASHBOARD as PlatformDashboard | undefined,
  isLoading: false,
  isError: false,
};
const audience = {
  data: AUDIENCE as PlatformAudience | undefined,
  isLoading: false,
  isError: false,
};

vi.mock("@/applications/platform/api/platform-api", () => ({
  usePlatformDashboard: () => dashboard,
  usePlatformAudience: () => audience,
}));

const { PlatformDashboardPage } = await import("./index");

Element.prototype.hasPointerCapture = () => false;
Element.prototype.scrollIntoView = () => {};

function audienceTiles(): HTMLElement {
  return screen.getByRole("region", { name: "Кто на платформе" });
}

describe("PlatformDashboardPage — the audience tiles", () => {
  beforeEach(() => {
    dashboard.data = DASHBOARD;
    dashboard.isError = false;
    audience.data = AUDIENCE;
  });

  it("counts cabinets, registry participants and teachers", () => {
    render(<PlatformDashboardPage />);

    const tiles = audienceTiles();
    expect(tiles).toHaveTextContent("Личные кабинеты");
    expect(tiles).toHaveTextContent("1 284");
    expect(tiles).toHaveTextContent("Участники в реестре");
    expect(tiles).toHaveTextContent("3 407");
    expect(tiles).toHaveTextContent("Педагоги");
    expect(tiles).toHaveTextContent("208");
  });

  it("names the subset beside each total instead of netting it out", () => {
    render(<PlatformDashboardPage />);

    const tiles = audienceTiles();
    expect(tiles).toHaveTextContent("902 с подтверждённой почтой");
    expect(tiles).toHaveTextContent("112 в архиве");
    expect(tiles).toHaveTextContent("7 в архиве");
  });

  it("says nothing rather than zero when the counts did not load", () => {
    audience.data = undefined;

    render(<PlatformDashboardPage />);

    // A missing read is not an empty platform: the tiles print an em dash, and the
    // funnel below them stays on screen.
    expect(audienceTiles()).toHaveTextContent("—");
    expect(audienceTiles()).not.toHaveTextContent("0");
    expect(screen.getByText("Сводка платформы")).toBeInTheDocument();
  });
});
