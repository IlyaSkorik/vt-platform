import { describe, expect, it } from "vitest";
import { bodyBlocks, heroBlock } from "./blocks";
import { makeBlock } from "./fixtures";

describe("landing block ordering", () => {
  const blocks = [
    makeBlock({ id: "venue", type: "VENUE", sortOrder: 3 }),
    makeBlock({ id: "hero", type: "HERO", sortOrder: 0 }),
    makeBlock({ id: "faq", type: "FAQ", sortOrder: 2 }),
    makeBlock({ id: "about", type: "CONTENT", sortOrder: 1 }),
  ];

  it("finds the single hero block", () => {
    expect(heroBlock(blocks)?.id).toBe("hero");
    expect(heroBlock([])).toBeNull();
  });

  it("returns body blocks in sort order, excluding the hero", () => {
    expect(bodyBlocks(blocks).map((block) => block.id)).toEqual(["about", "faq", "venue"]);
  });

  it("does not mutate the input array", () => {
    const input = [...blocks];
    bodyBlocks(input);
    expect(input).toEqual(blocks);
  });
});
