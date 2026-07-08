import type { UseQueryResult } from "@tanstack/react-query";
import type { WidgetStatus } from "../model";

/**
 * Collapse a TanStack Query result + emptiness check into the discrete
 * {@link WidgetStatus} every dashboard widget renders. Centralizing this keeps
 * the four-state contract (loading / error / empty / success) identical across
 * widgets instead of each re-deriving booleans from the query.
 */
export function deriveWidgetStatus(
  query: Pick<UseQueryResult, "isLoading" | "isError">,
  isEmpty: boolean,
): WidgetStatus {
  if (query.isLoading) {
    return "loading";
  }
  if (query.isError) {
    return "error";
  }
  return isEmpty ? "empty" : "success";
}
