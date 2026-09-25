import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAutosave } from "./use-autosave";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useAutosave", () => {
  it("saves once, after the typing settles", () => {
    const save = vi.fn();
    const { result } = renderHook(() => useAutosave(save, 700));

    act(() => result.current.schedule("Ив"));
    act(() => result.current.schedule("Иванова"));
    act(() => vi.advanceTimersByTime(699));
    expect(save).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(1));

    expect(save).toHaveBeenCalledExactlyOnceWith("Иванова");
  });

  it("sends what is waiting when the field goes away", () => {
    // Collapsing a card or leaving the page used to clear the timer, and the last
    // seconds of typing were never written anywhere.
    const save = vi.fn();
    const { result, unmount } = renderHook(() => useAutosave(save, 700));

    act(() => result.current.schedule("Иванова"));
    unmount();

    expect(save).toHaveBeenCalledExactlyOnceWith("Иванова");
  });

  it("sends what is waiting when the page is being hidden", () => {
    const save = vi.fn();
    const { result } = renderHook(() => useAutosave(save, 700));

    act(() => result.current.schedule("Иванова"));
    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    expect(save).toHaveBeenCalledExactlyOnceWith("Иванова");
  });

  it("writes nothing when nothing is waiting", () => {
    const save = vi.fn();
    const { result, unmount } = renderHook(() => useAutosave(save, 700));

    act(() => result.current.flush());
    act(() => vi.advanceTimersByTime(2000));
    unmount();

    expect(save).not.toHaveBeenCalled();
  });

  it("drops an edit that was typed back to where it started", () => {
    const save = vi.fn();
    const { result, unmount } = renderHook(() => useAutosave(save, 700));

    act(() => result.current.schedule("Иванова"));
    act(() => result.current.cancel());
    act(() => vi.advanceTimersByTime(2000));
    unmount();

    expect(save).not.toHaveBeenCalled();
  });

  it("uses the latest save, not the one captured when scheduling", () => {
    const first = vi.fn();
    const second = vi.fn();
    const { result, rerender } = renderHook(({ save }) => useAutosave(save, 700), {
      initialProps: { save: first },
    });

    act(() => result.current.schedule("Иванова"));
    rerender({ save: second });
    act(() => vi.advanceTimersByTime(700));

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledExactlyOnceWith("Иванова");
  });
});
