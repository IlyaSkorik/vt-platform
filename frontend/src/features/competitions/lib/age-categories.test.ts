import { describe, expect, it } from "vitest";
import type { _AgeCategory, _Category } from "@/shared/api/generated/model-competitions";
import {
  buildAgeCategoryReorderUpdates,
  buildAgeCategoryTree,
  createAgeCategoryPayload,
  duplicateAgeCategoryDraft,
  filterAgeCategoryTree,
  formatAgeRange,
  nextAgeCategorySortOrder,
} from "./age-categories";

function nomination(partial: Partial<_Category> & Pick<_Category, "id" | "name">): _Category {
  return {
    description: null,
    sortOrder: 0,
    ...partial,
  };
}

function age(
  partial: Partial<_AgeCategory> & Pick<_AgeCategory, "id" | "categoryId" | "name">,
): _AgeCategory {
  return {
    minAge: 0,
    maxAge: 0,
    sortOrder: 0,
    type: "STANDARD",
    mixedCalculationMethod: null,
    ...partial,
  };
}

describe("age category helpers", () => {
  it("builds a nomination → age categories tree", () => {
    const tree = buildAgeCategoryTree(
      [
        nomination({ id: "n2", name: "Dance", sortOrder: 1 }),
        nomination({ id: "n1", name: "Vocal", sortOrder: 0 }),
      ],
      [
        age({ id: "a2", categoryId: "n1", name: "7–9", minAge: 7, maxAge: 9, sortOrder: 1 }),
        age({ id: "a1", categoryId: "n1", name: "4–6", minAge: 4, maxAge: 6, sortOrder: 0 }),
        age({ id: "a3", categoryId: "n2", name: "5–7", minAge: 5, maxAge: 7, sortOrder: 0 }),
      ],
    );
    expect(tree.map((node) => node.nomination.id)).toEqual(["n1", "n2"]);
    expect(tree[0]?.ageCategories.map((item) => item.name)).toEqual(["4–6", "7–9"]);
  });

  it("filters by nomination and age category names", () => {
    const tree = buildAgeCategoryTree(
      [nomination({ id: "n1", name: "Vocal" }), nomination({ id: "n2", name: "Dance" })],
      [
        age({ id: "a1", categoryId: "n1", name: "Juniors", minAge: 4, maxAge: 6 }),
        age({ id: "a2", categoryId: "n2", name: "Seniors", minAge: 14, maxAge: 17 }),
      ],
    );
    expect(filterAgeCategoryTree(tree, "dance").map((node) => node.nomination.id)).toEqual(["n2"]);
    expect(
      filterAgeCategoryTree(tree, "junior")[0]?.ageCategories.map((item) => item.name),
    ).toEqual(["Juniors"]);
  });

  it("scopes next sort order and duplicate draft to nomination", () => {
    expect(
      nextAgeCategorySortOrder(
        [
          age({ id: "a1", categoryId: "n1", name: "A", sortOrder: 2 }),
          age({ id: "a2", categoryId: "n2", name: "B", sortOrder: 9 }),
        ],
        "n1",
      ),
    ).toBe(3);

    expect(
      duplicateAgeCategoryDraft(
        age({
          id: "a1",
          categoryId: "n1",
          name: "7–9 лет",
          minAge: 7,
          maxAge: 9,
          type: "MIXED",
          mixedCalculationMethod: "AVERAGE",
        }),
      ),
    ).toEqual({
      categoryId: "n1",
      name: "7–9 лет (копия)",
      minAge: 7,
      maxAge: 9,
      type: "MIXED",
      mixedCalculationMethod: "AVERAGE",
    });
  });

  it("builds create payload and reorder updates", () => {
    expect(
      createAgeCategoryPayload({
        categoryId: "n1",
        name: " 4–6 ",
        minAge: 4,
        maxAge: 6,
        type: "STANDARD",
        mixedCalculationMethod: "AVERAGE",
        sortOrder: 0,
      }),
    ).toEqual({
      categoryId: "n1",
      name: "4–6",
      minAge: 4,
      maxAge: 6,
      type: "STANDARD",
      mixedCalculationMethod: null,
      sortOrder: 0,
    });

    expect(formatAgeRange(26, 120)).toBe("26+");
    expect(
      buildAgeCategoryReorderUpdates(
        ["b", "a"],
        [
          age({ id: "a", categoryId: "n1", name: "A", sortOrder: 0 }),
          age({ id: "b", categoryId: "n1", name: "B", sortOrder: 1 }),
        ],
      ),
    ).toEqual([
      { ageCategoryId: "b", payload: { sortOrder: 0 } },
      { ageCategoryId: "a", payload: { sortOrder: 1 } },
    ]);
  });
});
