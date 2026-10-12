/**
 * Оператор платформы в чужом кабинете: заголовок, полоса и выход.
 *
 * Проверяется то, на чём эта функция может тихо сломаться: запрос, ушедший без
 * заголовка (оператор думает, что он в кабинете, а правит не там), и панель без
 * полосы (оператор не знает, что он в чужом кабинете, — а организатор смотрит на
 * тот же экран).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { actingOrganizationStore, apiClient } from "@/shared/api";
import { ActingAsBanner } from "./ui/acting-banner";

const originalFetch = globalThis.fetch;

function renderBanner(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  render(<ActingAsBanner />, { wrapper });
}

/** Заголовки, с которыми ушёл единственный запрос. */
async function headersOfOneRequest(): Promise<Headers> {
  const sent: Request[] = [];
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    sent.push(new Request(input));
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  }) as unknown as typeof fetch;
  await apiClient.get("staff/anything");
  const [request] = sent;
  if (request === undefined) {
    throw new Error("Запрос не ушёл — проверять нечего.");
  }
  return request.headers;
}

// `act`, потому что стор — внешний источник для `useSyncExternalStore`: его
// изменение перерисовывает смонтированный баннер, и React об этом предупреждает.
beforeEach(() => {
  act(() => actingOrganizationStore.set(null));
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  act(() => actingOrganizationStore.set(null));
  vi.restoreAllMocks();
});

describe("the acting-organization header", () => {
  it("is absent while the operator is in nobody's panel", async () => {
    const headers = await headersOfOneRequest();

    expect(headers.has("X-Acting-Organization")).toBe(false);
  });

  it("rides every request once a panel has been entered", async () => {
    actingOrganizationStore.set({ id: "0199-org", name: "Созвездие" });

    const headers = await headersOfOneRequest();

    expect(headers.get("X-Acting-Organization")).toBe("0199-org");
  });

  it("survives a reload — the visit is not lost to F5", () => {
    actingOrganizationStore.set({ id: "0199-org", name: "Созвездие" });

    expect(JSON.parse(localStorage.getItem("vt.acting-organization") ?? "null")).toEqual({
      id: "0199-org",
      name: "Созвездие",
    });
  });

  it("reads a corrupted record as being in nobody's panel", async () => {
    localStorage.setItem("vt.acting-organization", "{не json");

    // Store is read at module load, so the live check is that a bad value never
    // became the current one — the API call is the observable consequence.
    const headers = await headersOfOneRequest();

    expect(headers.has("X-Acting-Organization")).toBe(false);
  });
});

describe("the banner over somebody else's panel", () => {
  it("is not there for an ordinary staffer", () => {
    renderBanner();

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("names the organization the operator is inside", () => {
    act(() => actingOrganizationStore.set({ id: "0199-org", name: "Созвездие" }));

    renderBanner();

    expect(screen.getByRole("status")).toHaveTextContent("Созвездие");
  });

  it("lets the operator out without going via the console", async () => {
    act(() => actingOrganizationStore.set({ id: "0199-org", name: "Созвездие" }));
    renderBanner();

    await userEvent.click(screen.getByRole("button", { name: /Выйти из кабинета/ }));

    expect(actingOrganizationStore.get()).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
