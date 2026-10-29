import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "@/shared/api/query-client";

import { type PublicProgram, usePublicProgram, useSetRowProgress } from "./api";

/**
 * The two ways a live screen stops telling the truth during a festival — both of them
 * silent, which is why they are pinned down here.
 */

const program = (progress: "PENDING" | "ON_STAGE"): PublicProgram => ({
  name: "Программа первого дня",
  slug: "Sound2345",
  competitionTitle: "Взлёт талантов",
  nomination: "Вокал",
  startsAt: null,
  totalSeconds: 0,
  controlsRunningOrder: true,
  columns: [{ key: "TIME", label: "Время", custom: false, sensitive: false }],
  rows: [
    {
      kind: "PERFORMANCE",
      cells: ["10:00"],
      progress,
      id: "11111111-1111-1111-1111-111111111111",
      backstage: false,
      note: "",
    },
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

  it("does not roll the host's screen back to a poll that was already in flight", async () => {
    const poll: { release: ((value: Response) => void) | null } = { release: null };
    const fetchMock = vi.fn(async (input: unknown, init?: RequestInit) => {
      // Ky hands fetch a `Request`, so the method is on the input, not on the init.
      const method = String(
        init?.method ?? (input instanceof Request ? input.method : "get"),
      ).toLowerCase();
      if (method !== "get") {
        return json(program("ON_STAGE"));
      }
      if (fetchMock.mock.calls.length === 1) {
        return json(program("PENDING"));
      }
      return new Promise<Response>((resolve, reject) => {
        poll.release = resolve;
        // Honour the abort the way the browser does: cancelling the poll is exactly
        // what the mutation waits on before it writes.
        const signal = init?.signal ?? (input instanceof Request ? input.signal : null);
        signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = wrapperFor();
    const { result } = renderHook(
      () => ({
        read: usePublicProgram("Sound2345"),
        mark: useSetRowProgress("Sound2345"),
      }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.read.data?.rows[0]?.progress).toBe("PENDING"));
    // A poll goes out and hangs…
    await waitFor(() => expect(poll.release).not.toBeNull(), { timeout: 9000 });

    // …the host marks the act, and the write answers first.
    result.current.mark.mutate({
      itemId: "11111111-1111-1111-1111-111111111111",
      progress: "ON_STAGE",
    });
    await waitFor(() => expect(result.current.read.data?.rows[0]?.progress).toBe("ON_STAGE"));

    // The stale poll lands afterwards carrying the table as it was before the press.
    poll.release?.(json(program("PENDING")));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(result.current.read.data?.rows[0]?.progress).toBe("ON_STAGE");
  }, 30000);
});
