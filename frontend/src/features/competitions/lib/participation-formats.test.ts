import { describe, expect, it } from "vitest";
import type { _ParticipationFormat } from "@/shared/api/generated/model-competitions";
import {
  buildParticipationFormatReorderUpdates,
  countEnabledFormats,
  createParticipationFormatPayload,
  duplicateParticipationFormatDraft,
  filterParticipationFormats,
  nextParticipationFormatSortOrder,
  sortParticipationFormats,
} from "./participation-formats";

function format(
  partial: Partial<_ParticipationFormat> & Pick<_ParticipationFormat, "id" | "name">,
): _ParticipationFormat {
  return {
    description: null,
    enabled: true,
    sortOrder: 0,
    ...partial,
  };
}

describe("participation format helpers", () => {
  it("sorts by sortOrder then name", () => {
    const items = sortParticipationFormats([
      format({ id: "b", name: "Online", sortOrder: 1 }),
      format({ id: "a", name: "In Person", sortOrder: 0 }),
      format({ id: "c", name: "Hybrid", sortOrder: 1 }),
    ]);
    expect(items.map((item) => item.id)).toEqual(["a", "c", "b"]);
  });

  it("filters by name and description", () => {
    const items = [
      format({ id: "a", name: "Очно", description: "На сцене" }),
      format({ id: "b", name: "Онлайн", description: "Видеосвязь" }),
    ];
    expect(filterParticipationFormats(items, "онлайн").map((item) => item.id)).toEqual(["b"]);
    expect(filterParticipationFormats(items, "сцене").map((item) => item.id)).toEqual(["a"]);
  });

  it("builds duplicate draft, next sort order, and payloads", () => {
    expect(
      nextParticipationFormatSortOrder([
        format({ id: "a", name: "A", sortOrder: 2 }),
        format({ id: "b", name: "B", sortOrder: 5 }),
      ]),
    ).toBe(6);

    expect(
      duplicateParticipationFormatDraft(
        format({ id: "a", name: "Очно", description: "Зал", enabled: false }),
      ),
    ).toEqual({
      name: "Очно (копия)",
      description: "Зал",
      enabled: false,
    });

    expect(
      createParticipationFormatPayload({
        name: "  Hybrid ",
        description: "  Mix  ",
        enabled: true,
        sortOrder: 1,
      }),
    ).toEqual({
      name: "Hybrid",
      description: "Mix",
      enabled: true,
      sortOrder: 1,
    });
  });

  it("builds reorder updates and counts enabled formats", () => {
    const items = [
      format({ id: "a", name: "A", sortOrder: 0, enabled: true }),
      format({ id: "b", name: "B", sortOrder: 1, enabled: false }),
    ];
    expect(buildParticipationFormatReorderUpdates(["b", "a"], items)).toEqual([
      { formatId: "b", payload: { sortOrder: 0 } },
      { formatId: "a", payload: { sortOrder: 1 } },
    ]);
    expect(countEnabledFormats(items)).toBe(1);
  });
});
