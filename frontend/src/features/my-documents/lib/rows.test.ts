import { describe, expect, it } from "vitest";
import { documentRows } from "./rows";
import type { MyDocument } from "./types";

const ENTRY = "01900000-0000-7000-8000-0000000000aa";
const OTHER_ENTRY = "01900000-0000-7000-8000-0000000000bb";

let counter = 0;

function makeDocument(overrides: Partial<MyDocument> = {}): MyDocument {
  counter += 1;
  return {
    id: `01900000-0000-7000-8000-00000000000${counter}`,
    documentType: "INDIVIDUAL_DIPLOMA",
    submissionId: ENTRY,
    number: "VT-2026-000001",
    participantName: "Ансамбль «Созвездие»",
    competitionTitle: "Восходящие таланты",
    nomination: "Вокал",
    degree: "Лауреат I степени",
    recipient: "Иванова Мария",
    fileUrl: "/media/diplomas/official/x/1.pdf",
    issuedAt: "2026-05-20T12:00:00Z",
    ...overrides,
  };
}

describe("documentRows", () => {
  it("collapses one entry's individual diplomas into a single bundle", () => {
    const rows = documentRows([
      makeDocument({ recipient: "Иванова Мария" }),
      makeDocument({ recipient: "Петров Пётр" }),
      makeDocument({ recipient: "Сидорова Анна" }),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ kind: "bundle", submissionId: ENTRY });
    expect(rows[0]?.kind === "bundle" && rows[0].documents).toHaveLength(3);
  });

  it("keeps the bundle where the list already put those documents", () => {
    const rows = documentRows([
      makeDocument({ documentType: "DIPLOMA", recipient: "" }),
      makeDocument({ recipient: "Иванова Мария" }),
      makeDocument({ recipient: "Петров Пётр" }),
      makeDocument({ documentType: "THANK_YOU", recipient: "Петрова Ольга" }),
    ]);

    // The collective's own diploma, then its members' bundle, then the letter — the
    // order the server sent, with one group standing in for two rows.
    expect(rows.map((row) => row.kind)).toEqual(["document", "bundle", "document"]);
  });

  it("bundles each entry separately", () => {
    const rows = documentRows([
      makeDocument({ submissionId: ENTRY }),
      makeDocument({ submissionId: ENTRY }),
      makeDocument({ submissionId: OTHER_ENTRY }),
      makeDocument({ submissionId: OTHER_ENTRY }),
    ]);

    // Two ensembles' diplomas in one archive is not a bundle anybody asked for — even
    // when they share a nomination or a name.
    expect(rows.map((row) => row.kind === "bundle" && row.submissionId)).toEqual([
      ENTRY,
      OTHER_ENTRY,
    ]);
  });

  it("leaves a lone individual diploma as an ordinary row", () => {
    const rows = documentRows([makeDocument()]);

    // An archive of one file is a worse download than the file.
    expect(rows.map((row) => row.kind)).toEqual(["document"]);
  });

  it("never bundles a kind that is not issued per member", () => {
    const rows = documentRows([
      makeDocument({ documentType: "THANK_YOU", recipient: "Петрова Ольга" }),
      makeDocument({ documentType: "THANK_YOU", recipient: "Сидоров Иван" }),
    ]);

    // Two letters on one entry are two different documents, not one set.
    expect(rows.map((row) => row.kind)).toEqual(["document", "document"]);
  });
});
