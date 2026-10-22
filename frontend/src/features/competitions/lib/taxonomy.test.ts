import { describe, expect, it } from "vitest";
import type { _Category, _Discipline } from "@/shared/api/generated/model-competitions";
import {
  buildCategoryReorderUpdates,
  buildDisciplineReorderUpdates,
  buildTaxonomyTree,
  filterTaxonomyTree,
  moveIdBefore,
  nextCategorySortOrder,
  nextDisciplineSortOrder,
} from "./taxonomy";

function category(partial: Partial<_Category> & Pick<_Category, "id" | "name">): _Category {
  return {
    description: null,
    sortOrder: 0,
    registrationOpensAt: null,
    registrationClosesAt: null,
    registrationStopped: false,
    waitlistEnabled: false,
    heldAt: null,
    editingLockedAt: null,
    ...partial,
  };
}

function discipline(
  partial: Partial<_Discipline> & Pick<_Discipline, "id" | "categoryId" | "name">,
): _Discipline {
  return {
    sortOrder: 0,
    ...partial,
  };
}

describe("taxonomy helpers", () => {
  it("builds a sorted category → disciplines tree", () => {
    const tree = buildTaxonomyTree(
      [
        category({ id: "c2", name: "Dance", sortOrder: 1 }),
        category({ id: "c1", name: "Vocal", sortOrder: 0 }),
      ],
      [
        discipline({ id: "d2", categoryId: "c1", name: "Folk", sortOrder: 1 }),
        discipline({ id: "d1", categoryId: "c1", name: "Pop", sortOrder: 0 }),
        discipline({ id: "d3", categoryId: "c2", name: "Classical", sortOrder: 0 }),
      ],
    );

    expect(tree.map((node) => node.category.id)).toEqual(["c1", "c2"]);
    expect(tree[0]?.disciplines.map((item) => item.name)).toEqual(["Pop", "Folk"]);
  });

  it("filters by category and discipline names", () => {
    const tree = buildTaxonomyTree(
      [
        category({ id: "c1", name: "Vocal", description: "Singing", sortOrder: 0 }),
        category({ id: "c2", name: "Dance", sortOrder: 1 }),
      ],
      [
        discipline({ id: "d1", categoryId: "c1", name: "Pop", sortOrder: 0 }),
        discipline({ id: "d2", categoryId: "c2", name: "Contemporary", sortOrder: 0 }),
      ],
    );

    expect(filterTaxonomyTree(tree, "sing").map((node) => node.category.id)).toEqual(["c1"]);
    expect(filterTaxonomyTree(tree, "contemp")[0]?.disciplines.map((item) => item.name)).toEqual([
      "Contemporary",
    ]);
  });

  it("suggests next sort orders", () => {
    expect(nextCategorySortOrder([])).toBe(0);
    expect(
      nextCategorySortOrder([
        category({ id: "c1", name: "A", sortOrder: 2 }),
        category({ id: "c2", name: "B", sortOrder: 5 }),
      ]),
    ).toBe(6);
    expect(
      nextDisciplineSortOrder(
        [
          discipline({ id: "d1", categoryId: "c1", name: "A", sortOrder: 1 }),
          discipline({ id: "d2", categoryId: "c2", name: "B", sortOrder: 9 }),
        ],
        "c1",
      ),
    ).toBe(2);
  });

  it("builds only changed reorder updates", () => {
    const categories = [
      category({ id: "c1", name: "A", sortOrder: 0 }),
      category({ id: "c2", name: "B", sortOrder: 1 }),
    ];
    expect(buildCategoryReorderUpdates(["c2", "c1"], categories)).toEqual([
      { categoryId: "c2", payload: { sortOrder: 0 } },
      { categoryId: "c1", payload: { sortOrder: 1 } },
    ]);

    const disciplines = [
      discipline({ id: "d1", categoryId: "c1", name: "A", sortOrder: 0 }),
      discipline({ id: "d2", categoryId: "c1", name: "B", sortOrder: 1 }),
    ];
    expect(buildDisciplineReorderUpdates(["d2", "d1"], disciplines)).toEqual([
      { disciplineId: "d2", payload: { sortOrder: 0 } },
      { disciplineId: "d1", payload: { sortOrder: 1 } },
    ]);
  });

  it("moves ids before a drop target", () => {
    expect(moveIdBefore(["a", "b", "c"], "c", "a")).toEqual(["c", "a", "b"]);
  });
});
