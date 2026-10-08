import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useStableViewportHeight } from "./use-stable-viewport-height";

/** Resize the window the way jsdom allows, then fire the event the hook listens to. */
function resizeTo(width: number, height: number): void {
  act(() => {
    window.innerWidth = width;
    window.innerHeight = height;
    window.dispatchEvent(new Event("resize"));
  });
}

describe("useStableViewportHeight", () => {
  let originalWidth: number;
  let originalHeight: number;

  beforeEach(() => {
    originalWidth = window.innerWidth;
    originalHeight = window.innerHeight;
    window.innerWidth = 390;
    window.innerHeight = 664;
  });

  afterEach(() => {
    window.innerWidth = originalWidth;
    window.innerHeight = originalHeight;
  });

  it("reports the height the window had on mount", () => {
    const { result } = renderHook(() => useStableViewportHeight());

    expect(result.current).toBe(664);
  });

  it("ignores a height-only resize — that is browser chrome collapsing, not a new viewport", () => {
    const { result } = renderHook(() => useStableViewportHeight());

    resizeTo(390, 724);

    expect(result.current).toBe(664);
  });

  it("follows a resize that moves the width too, which is a rotation or a real window drag", () => {
    const { result } = renderHook(() => useStableViewportHeight());

    resizeTo(844, 390);

    expect(result.current).toBe(390);
  });

  it("stops listening once unmounted", () => {
    const { result, unmount } = renderHook(() => useStableViewportHeight());

    unmount();
    resizeTo(844, 390);

    expect(result.current).toBe(664);
  });
});
