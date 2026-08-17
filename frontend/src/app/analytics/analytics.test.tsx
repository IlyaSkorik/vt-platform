import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAnalyticsConsent } from "@/features/cookie-consent";
import { Analytics } from "./analytics";
import { startAnalytics, stopAnalytics, trackPageView } from "./trackers";

vi.mock("@/features/cookie-consent", () => ({ useAnalyticsConsent: vi.fn() }));
vi.mock("./trackers", () => ({
  startAnalytics: vi.fn(() => true),
  stopAnalytics: vi.fn(() => false),
  trackPageView: vi.fn(),
}));

const consent = vi.mocked(useAnalyticsConsent);

function renderAt(at: string): void {
  render(
    <MemoryRouter initialEntries={[at]}>
      <Analytics />
      <Routes>
        <Route path="/" element={<Link to="/festivals?page=2">Фестивали</Link>} />
        <Route path="/festivals" element={<span>Фестивали</span>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Analytics", () => {
  it("loads nothing and reports nothing without a decision", () => {
    consent.mockReturnValue(false);

    renderAt("/");

    expect(startAnalytics).not.toHaveBeenCalled();
    expect(trackPageView).not.toHaveBeenCalled();
  });

  it("does not reload a page that never started counting", () => {
    consent.mockReturnValue(false);

    renderAt("/");

    // Withdrawal is what reloads, and there is nothing to withdraw on a first visit
    // with the banner still open.
    expect(stopAnalytics).not.toHaveBeenCalled();
  });

  it("loads the counters and records the page once consent is given", () => {
    consent.mockReturnValue(true);

    renderAt("/");

    expect(startAnalytics).toHaveBeenCalledTimes(1);
    expect(trackPageView).toHaveBeenCalledWith("/");
  });

  it("records every navigation, not just the first page", async () => {
    const user = userEvent.setup();
    consent.mockReturnValue(true);
    renderAt("/");

    await user.click(document.querySelector("a") as HTMLAnchorElement);

    expect(trackPageView).toHaveBeenLastCalledWith("/festivals?page=2");
    expect(startAnalytics).toHaveBeenCalledTimes(1);
  });

  it("stops the counters when the decision is withdrawn", () => {
    consent.mockReturnValue(true);
    const { rerender } = render(
      <MemoryRouter initialEntries={["/"]}>
        <Analytics />
      </MemoryRouter>,
    );
    consent.mockReturnValue(false);

    rerender(
      <MemoryRouter initialEntries={["/"]}>
        <Analytics />
      </MemoryRouter>,
    );

    expect(stopAnalytics).toHaveBeenCalledTimes(1);
  });
});
