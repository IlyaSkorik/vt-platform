import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RouteHydrateFallback } from "./route-hydrate-fallback";
import { routes } from "./router";

describe("RouteHydrateFallback", () => {
  it("announces the wait rather than showing an empty page", () => {
    render(<RouteHydrateFallback />);

    // `role="status"` so a screen reader says something during the wait; a blank
    // screen announces nothing at all, which is the state this replaces.
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Загрузка")).toBeInTheDocument();
  });

  it("is attached to the root route, which is the only place it can run", () => {
    // React Router renders a hydrate fallback from the *root* match only. On a
    // child it is silently unused and the first paint goes back to being blank.
    expect(routes[0]?.HydrateFallback).toBe(RouteHydrateFallback);
  });
});
