import { describe, expect, it } from "vitest";
import type { _Category, _ParticipantGroup } from "@/shared/api/generated/model-competitions";
import {
  buildParticipantGroupReorderUpdates,
  buildParticipantGroupTree,
  createParticipantGroupPayload,
  duplicateParticipantGroupDraft,
  filterParticipantGroupTree,
  formatParticipantRange,
  nextParticipantGroupSortOrder,
} from "./participant-groups";

function nomination(partial: Partial<_Category> & Pick<_Category, "id" | "name">): _Category {
  return {
    description: null,
    sortOrder: 0,
    ...partial,
  };
}

function group(
  partial: Partial<_ParticipantGroup> & Pick<_ParticipantGroup, "id" | "categoryId" | "name">,
): _ParticipantGroup {
  return {
    minCount: 1,
    maxCount: 1,
    description: null,
    sortOrder: 0,
    ...partial,
  };
}

describe("participant group helpers", () => {
  it("builds a nomination → groups tree", () => {
    const tree = buildParticipantGroupTree(
      [
        nomination({ id: "n2", name: "Dance", sortOrder: 1 }),
        nomination({ id: "n1", name: "Vocal", sortOrder: 0 }),
      ],
      [
        group({ id: "g2", categoryId: "n1", name: "Duet", minCount: 2, maxCount: 2, sortOrder: 1 }),
        group({ id: "g1", categoryId: "n1", name: "Solo", minCount: 1, maxCount: 1, sortOrder: 0 }),
        group({
          id: "g3",
          categoryId: "n2",
          name: "Ensemble",
          minCount: 5,
          maxCount: 12,
          sortOrder: 0,
        }),
      ],
    );
    expect(tree.map((node) => node.nomination.id)).toEqual(["n1", "n2"]);
    expect(tree[0]?.groups.map((item) => item.name)).toEqual(["Solo", "Duet"]);
  });

  it("formats participant ranges", () => {
    expect(formatParticipantRange(1, 1)).toBe("1");
    expect(formatParticipantRange(5, 12)).toBe("5–12");
    expect(formatParticipantRange(6, null)).toBe("6+");
  });

  it("filters by nomination and group fields", () => {
    const tree = buildParticipantGroupTree(
      [nomination({ id: "n1", name: "Vocal" }), nomination({ id: "n2", name: "Dance" })],
      [
        group({
          id: "g1",
          categoryId: "n1",
          name: "Solo",
          description: "Один участник",
        }),
        group({ id: "g2", categoryId: "n2", name: "Choir", minCount: 16, maxCount: 40 }),
      ],
    );
    expect(filterParticipantGroupTree(tree, "dance").map((node) => node.nomination.id)).toEqual([
      "n2",
    ]);
    expect(filterParticipantGroupTree(tree, "один")[0]?.groups.map((item) => item.name)).toEqual([
      "Solo",
    ]);
  });

  it("scopes next sort order and duplicate draft", () => {
    expect(
      nextParticipantGroupSortOrder(
        [
          group({ id: "g1", categoryId: "n1", name: "A", sortOrder: 2 }),
          group({ id: "g2", categoryId: "n2", name: "B", sortOrder: 9 }),
        ],
        "n1",
      ),
    ).toBe(3);

    expect(
      duplicateParticipantGroupDraft(
        group({
          id: "g1",
          categoryId: "n1",
          name: "Solo",
          minCount: 1,
          maxCount: 1,
          description: "One",
        }),
      ),
    ).toEqual({
      categoryId: "n1",
      name: "Solo (копия)",
      minCount: 1,
      maxCount: 1,
      description: "One",
    });
  });

  it("builds reorder updates and create payloads", () => {
    expect(
      buildParticipantGroupReorderUpdates(
        ["g2", "g1"],
        [
          group({ id: "g1", categoryId: "n1", name: "A", sortOrder: 0 }),
          group({ id: "g2", categoryId: "n1", name: "B", sortOrder: 1 }),
        ],
      ),
    ).toEqual([
      { participantGroupId: "g2", payload: { sortOrder: 0 } },
      { participantGroupId: "g1", payload: { sortOrder: 1 } },
    ]);

    expect(
      createParticipantGroupPayload({
        categoryId: "n1",
        name: "  Ensemble ",
        minCount: 5,
        maxCount: 12,
        description: "  Small group  ",
        sortOrder: 2,
      }),
    ).toEqual({
      categoryId: "n1",
      name: "Ensemble",
      minCount: 5,
      maxCount: 12,
      description: "Small group",
      sortOrder: 2,
    });
  });
});
