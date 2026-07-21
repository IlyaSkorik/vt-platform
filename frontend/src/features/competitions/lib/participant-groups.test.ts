import { describe, expect, it } from "vitest";
import type { _ParticipantGroup } from "@/shared/api/generated/model-competitions";
import {
  buildParticipantGroupReorderUpdates,
  createParticipantGroupPayload,
  duplicateParticipantGroupDraft,
  filterParticipantGroups,
  formatParticipantRange,
  nextParticipantGroupSortOrder,
} from "./participant-groups";

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

describe("participant group helpers", () => {
  it("filters and sorts the flat competition-wide list", () => {
    const filtered = filterParticipantGroups(
      [
        group({ id: "g2", name: "Duet", minCount: 2, maxCount: 2, sortOrder: 1 }),
        group({ id: "g1", name: "Solo", minCount: 1, maxCount: 1, sortOrder: 0 }),
        group({ id: "g3", name: "Ensemble", minCount: 5, maxCount: 12, sortOrder: 2 }),
      ],
      "",
    );
    expect(filtered.map((item) => item.id)).toEqual(["g1", "g2", "g3"]);
  });

  it("formats participant ranges", () => {
    expect(formatParticipantRange(1, 1)).toBe("1");
    expect(formatParticipantRange(5, 12)).toBe("5–12");
    expect(formatParticipantRange(6, null)).toBe("6+");
  });

  it("filters by group name and description", () => {
    const groups = [
      group({ id: "g1", name: "Solo", description: "Один участник" }),
      group({ id: "g2", name: "Choir", minCount: 16, maxCount: 40 }),
    ];
    expect(filterParticipantGroups(groups, "choir").map((item) => item.id)).toEqual(["g2"]);
    expect(filterParticipantGroups(groups, "один").map((item) => item.name)).toEqual(["Solo"]);
  });

  it("computes next sort order across the whole list and duplicate draft", () => {
    expect(
      nextParticipantGroupSortOrder([
        group({ id: "g1", name: "A", sortOrder: 2 }),
        group({ id: "g2", name: "B", sortOrder: 9 }),
      ]),
    ).toBe(10);

    expect(nextParticipantGroupSortOrder([])).toBe(0);

    expect(
      duplicateParticipantGroupDraft(
        group({
          id: "g1",
          name: "Solo",
          minCount: 1,
          maxCount: 1,
          description: "One",
        }),
      ),
    ).toEqual({
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
          group({ id: "g1", name: "A", sortOrder: 0 }),
          group({ id: "g2", name: "B", sortOrder: 1 }),
        ],
      ),
    ).toEqual([
      { participantGroupId: "g2", payload: { sortOrder: 0 } },
      { participantGroupId: "g1", payload: { sortOrder: 1 } },
    ]);

    expect(
      createParticipantGroupPayload({
        name: "  Ensemble ",
        minCount: 5,
        maxCount: 12,
        description: "  Small group  ",
        sortOrder: 2,
      }),
    ).toEqual({
      name: "Ensemble",
      minCount: 5,
      maxCount: 12,
      description: "Small group",
      sortOrder: 2,
    });
  });
});
