import { describe, expect, it } from "vitest";
import type { _Document } from "@/shared/api/generated/model-competitions";
import { createUuidV7 } from "@/shared/lib";
import {
  buildReorderedSortUpdates,
  filterAndSortDocuments,
  nextDocumentSortOrder,
} from "./documents";

function document(
  partial: Partial<_Document> & Pick<_Document, "id" | "title" | "sortOrder">,
): _Document {
  return {
    category: "OTHER",
    visibility: "PUBLIC",
    fileReference: "/media/doc.pdf",
    description: null,
    published: false,
    ...partial,
  };
}

describe("documents helpers", () => {
  it("filters by title and description", () => {
    const items = [
      document({ id: "1", title: "Программа", description: "День 1", sortOrder: 0 }),
      document({ id: "2", title: "Реквизиты", description: "Банк", sortOrder: 1 }),
    ];
    expect(filterAndSortDocuments(items, "банк", "manual").map((item) => item.id)).toEqual(["2"]);
  });

  it("sorts by title", () => {
    const items = [
      document({ id: "1", title: "Б", sortOrder: 1 }),
      document({ id: "2", title: "А", sortOrder: 0 }),
    ];
    expect(filterAndSortDocuments(items, "", "title-asc").map((item) => item.title)).toEqual([
      "А",
      "Б",
    ]);
  });

  it("suggests the next sort order", () => {
    expect(nextDocumentSortOrder([])).toBe(0);
    expect(
      nextDocumentSortOrder([
        document({ id: "1", title: "A", sortOrder: 2 }),
        document({ id: "2", title: "B", sortOrder: 5 }),
      ]),
    ).toBe(6);
  });

  it("builds only changed sort updates after reorder", () => {
    const idA = createUuidV7();
    const idB = createUuidV7();
    const items = [
      document({ id: idA, title: "A", sortOrder: 0 }),
      document({ id: idB, title: "B", sortOrder: 1 }),
    ];
    const updates = buildReorderedSortUpdates([idB, idA], items);
    expect(updates).toHaveLength(2);
    expect(updates[0]?.documentId).toBe(idB);
    expect(updates[0]?.values.sortOrder).toBe(0);
    expect(updates[1]?.documentId).toBe(idA);
    expect(updates[1]?.values.sortOrder).toBe(1);
  });
});
