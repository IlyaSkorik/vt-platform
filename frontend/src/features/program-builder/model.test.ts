import { describe, expect, it } from "vitest";

import { moveItem } from "./model";

/**
 * `moveItem` is the only place the running order is rearranged client-side: the reorder
 * endpoint takes the complete new order, so a wrong result here would silently send a
 * different programme than the organizer sees.
 */
describe("moveItem", () => {
  it("moves an item down one place", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
  });

  it("moves an item up one place", () => {
    expect(moveItem(["a", "b", "c"], 2, 1)).toEqual(["a", "c", "b"]);
  });

  it("keeps every item, so a reorder can never drop a slot", () => {
    const result = moveItem(["a", "b", "c", "d"], 3, 0);
    expect(result).toEqual(["d", "a", "b", "c"]);
    expect(result).toHaveLength(4);
  });

  it("returns an unchanged copy when the move is a no-op", () => {
    const items = ["a", "b"];
    expect(moveItem(items, 1, 1)).toEqual(items);
  });

  it("ignores out-of-range indices instead of corrupting the order", () => {
    expect(moveItem(["a", "b"], 0, 5)).toEqual(["a", "b"]);
    expect(moveItem(["a", "b"], -1, 0)).toEqual(["a", "b"]);
  });

  it("does not mutate the input", () => {
    const items = ["a", "b", "c"];
    moveItem(items, 0, 2);
    expect(items).toEqual(["a", "b", "c"]);
  });
});
