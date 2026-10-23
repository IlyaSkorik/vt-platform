import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "@/shared/api/query-client";

import { type PublicProgram, usePublicProgram } from "./api";

/**
 * How a live screen stops telling the truth during a festival — silently, which is why
 * it is pinned down here.
 */

const program = (progress: "PENDING" | "ON_STAGE"): PublicProgram => ({
  name: "Программа первого дня",
  slug: "Sound2345",
  competitionTitle: "Взлёт талантов",
  nomination: "Вокал",
  startsAt: null,
  totalSeconds: 0,
  controlsRunningOrder: true,
  columns: [{ key: "TIME", label: "Время", custom: false }],
  rows: [
    { kind: "PERFORMANCE", cells: ["10:00"], progress, id: "11111111-1111-1111-1111-111111111111" },
  ],
});

function json(body: PublicProgram): Response {
  return new Response(JSON.stringify({ data: body }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function wrapperFor(): ({ children }: { children: React.ReactNode }) => React.JSX.Element {
  const client = createQueryClient();
  return ({ children }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", { value: state, configurable: true });
  // The manager listens on `window`, which is where the real event ends up by bubbling.
  window.dispatchEvent(new Event("visibilitychange"));
}

describe("a screen that was switched away from", () => {
  beforeEach(() => {
    setVisibility("visible");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setVisibility("visible");
  });

  it("starts polling again when the viewer comes back", async () => {
    const fetchMock = vi.fn(async () => json(program("PENDING")));
    vi.stubGlobal("fetch", fetchMock);

    renderHook(() => usePublicProgram("Sound2345"), { wrapper: wrapperFor() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Away: the poll stops itself on the tick that finds the page hidden.
    setVisibility("hidden");
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(1), { timeout: 9000 });
    const whileAway = fetchMock.mock.calls.length;

    // Back: without a refetch on focus nothing ever recomputes the interval, and this
    // screen would show the running order frozen at the moment of the switch.
    setVisibility("visible");
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(whileAway + 1), {
      timeout: 9000,
    });
  }, 30000);
});
