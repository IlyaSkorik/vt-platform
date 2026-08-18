import { describe, expect, it } from "vitest";
import { DOCUMENT_KINDS, documentKind, documentRecipient, documentSubtitle } from "./kinds";
import type { MyDocument } from "./types";

function makeDocument(overrides: Partial<MyDocument> = {}): MyDocument {
  return {
    id: "01900000-0000-7000-8000-000000000001",
    documentType: "THANK_YOU",
    submissionId: "01900000-0000-7000-8000-0000000000aa",
    number: null,
    participantName: "Иванов Иван",
    competitionTitle: "Восходящие таланты",
    nomination: "Вокал",
    degree: null,
    recipient: "Петрова Ольга",
    fileUrl: "/media/diplomas/documents/x/thank_you/1.pdf",
    issuedAt: "2026-05-20T12:00:00Z",
    ...overrides,
  };
}

describe("documentKind", () => {
  it("labels the two kinds the platform issues", () => {
    expect(documentKind("DIPLOMA").label).toBe("Диплом");
    expect(documentKind("THANK_YOU").label).toBe("Благодарность");
  });

  it("marks each kind with a drawn icon rather than an emoji", () => {
    // An emoji is rendered by the operating system: the same row looked like a
    // gold trophy on one machine and a flat grey glyph on another.
    for (const kind of [
      documentKind("DIPLOMA"),
      documentKind("THANK_YOU"),
      documentKind("CERTIFICATE"),
    ]) {
      expect(typeof kind.icon).not.toBe("string");
    }
  });

  it("gives the diploma and the thank-you letter tints of their own", () => {
    expect(documentKind("DIPLOMA").tone).not.toBe(documentKind("THANK_YOU").tone);
    expect(documentKind("CERTIFICATE").tone).toBe("neutral");
  });

  it("shows a number and a degree only for the diploma", () => {
    expect(DOCUMENT_KINDS.DIPLOMA).toMatchObject({ showsNumber: true, showsDegree: true });
    // A thank-you letter is not numbered and ranks nothing.
    expect(DOCUMENT_KINDS.THANK_YOU).toMatchObject({ showsNumber: false, showsDegree: false });
  });

  it("falls back rather than throwing on a kind this build does not know", () => {
    // A backend deploy ahead of a frontend one must degrade, not blank the page.
    const kind = documentKind("CERTIFICATE");
    expect(kind.label).toBe("Документ");
    expect(kind.showsNumber).toBe(false);
  });
});

describe("documentSubtitle", () => {
  it("joins the competition and the nomination", () => {
    expect(documentSubtitle(makeDocument())).toBe("Восходящие таланты · Вокал");
  });

  it("drops the parts the snapshot does not carry", () => {
    expect(documentSubtitle(makeDocument({ nomination: null }))).toBe("Восходящие таланты");
    expect(documentSubtitle(makeDocument({ competitionTitle: "  " }))).toBe("Вокал");
  });

  it("has nothing to show when neither is known", () => {
    expect(documentSubtitle(makeDocument({ competitionTitle: null, nomination: null }))).toBeNull();
  });
});

describe("documentRecipient", () => {
  it("names who an addressed document is for", () => {
    // Two letters on one entry are otherwise identical rows.
    expect(documentRecipient(makeDocument())).toBe("Петрова Ольга");
  });

  it("has nothing to show for a document that belongs to the performance", () => {
    expect(documentRecipient(makeDocument({ documentType: "DIPLOMA", recipient: "" }))).toBeNull();
    expect(documentRecipient(makeDocument({ recipient: "   " }))).toBeNull();
  });
});
