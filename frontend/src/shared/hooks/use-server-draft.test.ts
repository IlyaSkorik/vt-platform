import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useServerDraft } from "./use-server-draft";

const isSame = (a: string, b: string): boolean => a === b;

describe("useServerDraft", () => {
  it("shows what the server holds until somebody types", () => {
    const { result, rerender } = renderHook(({ server }) => useServerDraft(server, isSame), {
      initialProps: { server: "Иванова" },
    });

    expect(result.current[0]).toBe("Иванова");

    rerender({ server: "Петрова" });

    expect(result.current[0]).toBe("Петрова");
  });

  it("never overwrites an unsaved edit with the echo of a save", () => {
    const { result, rerender } = renderHook(({ server }) => useServerDraft(server, isSame), {
      initialProps: { server: "" },
    });

    act(() => result.current[1]("Иванова"));
    // The order comes back carrying the save that has just landed.
    rerender({ server: "Иванова Анна" });

    expect(result.current[0]).toBe("Иванова");
  });

  it("is in step with the server again once the edit is stored", () => {
    const { result, rerender } = renderHook(({ server }) => useServerDraft(server, isSame), {
      initialProps: { server: "" },
    });

    act(() => result.current[1]("Иванова"));
    rerender({ server: "Иванова" });
    // A later change from elsewhere — another tab, an organizer — lands normally.
    rerender({ server: "Петрова" });

    expect(result.current[0]).toBe("Петрова");
  });

  it("ignores a value that is merely rebuilt by a refetch", () => {
    // The identity of the stored value changes on every render; only its content says
    // whether anything actually happened.
    let renders = 0;
    const { result, rerender } = renderHook(
      ({ server }) => {
        renders += 1;
        return useServerDraft(server, (a: string[], b: string[]) => a.join("|") === b.join("|"));
      },
      { initialProps: { server: ["Иванова"] } },
    );

    act(() => result.current[1](["Иванова", "Петров"]));
    rerender({ server: ["Иванова"] });

    expect(result.current[0]).toEqual(["Иванова", "Петров"]);
    expect(renders).toBeGreaterThan(0);
  });
});
