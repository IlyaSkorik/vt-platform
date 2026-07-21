import { describe, expect, it } from "vitest";
import type { _AgeCategory, _ParticipantGroup } from "@/shared/api/generated/model-competitions";
import {
  buildAgeCategoryReorderUpdates,
  buildAgeCategoryTree,
  createAgeCategoryPayload,
  duplicateAgeCategoryDraft,
  filterAgeCategoryTree,
  formatAgeRange,
  nextAgeCategorySortOrder,
} from "./age-categories";

function group(
  partial: Partial<_ParticipantGroup> & Pick<_ParticipantGroup, "id" | "name">,
): _ParticipantGroup {
  return {
    minCount: 1,
    maxCount: 1,
    description: null,
    sortOrder: 0,
    ...partial,
  };
}

function age(
  partial: Partial<_AgeCategory> & Pick<_AgeCategory, "id" | "participantGroupId" | "name">,
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
  it("builds a participant group → age categories tree", () => {
    const tree = buildAgeCategoryTree(
      [
        group({ id: "g2", name: "Duet", sortOrder: 1 }),
        group({ id: "g1", name: "Solo", sortOrder: 0 }),
      ],
      [
        age({
          id: "a2",
          participantGroupId: "g1",
          name: "7–9",
          minAge: 7,
          maxAge: 9,
          sortOrder: 1,
        }),
        age({
          id: "a1",
          participantGroupId: "g1",
          name: "4–6",
          minAge: 4,
          maxAge: 6,
          sortOrder: 0,
        }),
        age({
          id: "a3",
          participantGroupId: "g2",
          name: "5–7",
          minAge: 5,
          maxAge: 7,
          sortOrder: 0,
        }),
      ],
    );
    expect(tree.map((node) => node.group.id)).toEqual(["g1", "g2"]);
    expect(tree[0]?.ageCategories.map((item) => item.name)).toEqual(["4–6", "7–9"]);
  });

  it("filters by participant group and age category names", () => {
    const tree = buildAgeCategoryTree(
      [group({ id: "g1", name: "Solo" }), group({ id: "g2", name: "Duet" })],
      [
        age({ id: "a1", participantGroupId: "g1", name: "Juniors", minAge: 4, maxAge: 6 }),
        age({ id: "a2", participantGroupId: "g2", name: "Seniors", minAge: 14, maxAge: 17 }),
      ],
    );
    expect(filterAgeCategoryTree(tree, "duet").map((node) => node.group.id)).toEqual(["g2"]);
    expect(
      filterAgeCategoryTree(tree, "junior")[0]?.ageCategories.map((item) => item.name),
    ).toEqual(["Juniors"]);
  });

  it("scopes next sort order and duplicate draft to participant group", () => {
    expect(
      nextAgeCategorySortOrder(
        [
          age({ id: "a1", participantGroupId: "g1", name: "A", sortOrder: 2 }),
          age({ id: "a2", participantGroupId: "g2", name: "B", sortOrder: 9 }),
        ],
        "g1",
      ),
    ).toBe(3);

    expect(
      duplicateAgeCategoryDraft(
        age({
          id: "a1",
          participantGroupId: "g1",
          name: "7–9 лет",
          minAge: 7,
          maxAge: 9,
          type: "MIXED",
          mixedCalculationMethod: "AVERAGE",
        }),
      ),
    ).toEqual({
      participantGroupId: "g1",
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
        participantGroupId: "g1",
        name: " 4–6 ",
        minAge: 4,
        maxAge: 6,
        type: "STANDARD",
        mixedCalculationMethod: "AVERAGE",
        sortOrder: 0,
      }),
    ).toEqual({
      participantGroupId: "g1",
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
          age({ id: "a", participantGroupId: "g1", name: "A", sortOrder: 0 }),
          age({ id: "b", participantGroupId: "g1", name: "B", sortOrder: 1 }),
        ],
      ),
    ).toEqual([
      { ageCategoryId: "b", payload: { sortOrder: 0 } },
      { ageCategoryId: "a", payload: { sortOrder: 1 } },
    ]);
  });
});
