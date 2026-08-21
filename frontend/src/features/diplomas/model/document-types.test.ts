import { describe, expect, it } from "vitest";
import { FIELD_TYPES } from "./constructor";
import { allowsFieldType, documentTypeConfig, requiresQrBlock } from "./document-types";

describe("allowsFieldType", () => {
  it("lets an individual diploma carry the whole catalogue", () => {
    for (const field of FIELD_TYPES) {
      expect(allowsFieldType("INDIVIDUAL_DIPLOMA", field.id)).toBe(true);
    }
  });

  it("lets a diploma carry everything but the member's name", () => {
    // The collective's own sheet has no one member to name, so a field bound to one
    // would print nothing there.
    for (const field of FIELD_TYPES) {
      expect(allowsFieldType("DIPLOMA", field.id)).toBe(field.id !== "member_name");
    }
  });

  it("keeps the member's name off a thank-you letter too", () => {
    expect(allowsFieldType("THANK_YOU", "member_name")).toBe(false);
  });

  it("limits a thank-you letter to who, who taught them, and where", () => {
    const allowed = FIELD_TYPES.filter((field) => allowsFieldType("THANK_YOU", field.id)).map(
      (field) => field.id,
    );
    expect(allowed).toEqual([
      "participant_name",
      "teacher",
      "competition_name",
      "competition_date",
      "competition_city",
      "free_text",
    ]);
  });

  it.each([
    "award_degree",
    "qr_block",
    "diploma_issue_date",
    "nomination_block",
    "work",
    "organization",
    "participant_age",
  ] as const)("keeps %s off a thank-you letter", (fieldType) => {
    // Each of these is legitimate on a diploma but meaningless on a courtesy letter,
    // and the backend rejects a layout carrying them.
    expect(allowsFieldType("THANK_YOU", fieldType)).toBe(false);
    expect(allowsFieldType("DIPLOMA", fieldType)).toBe(true);
  });

  it("treats an unknown kind as unrestricted rather than empty", () => {
    // A client running behind the backend still shows a usable palette.
    expect(allowsFieldType("CERTIFICATE", "award_degree")).toBe(true);
  });
});

describe("documentTypeConfig", () => {
  it("names the slot each kind fills on a nomination", () => {
    expect(documentTypeConfig("DIPLOMA").slotLabel).toBe("Шаблон диплома");
    expect(documentTypeConfig("INDIVIDUAL_DIPLOMA").slotLabel).toBe(
      "Шаблон индивидуального диплома",
    );
    expect(documentTypeConfig("THANK_YOU").slotLabel).toBe("Шаблон благодарности");
  });

  it("falls back for a kind this build does not know", () => {
    expect(documentTypeConfig("CERTIFICATE").label).toBe("Документ");
  });
});

describe("requiresQrBlock", () => {
  it("requires it on both kinds of diploma", () => {
    // Numbered and verifiable: the block is the only place the number and the
    // verification link are printed, so a layout without one issues a sheet nobody
    // can check.
    expect(requiresQrBlock("DIPLOMA")).toBe(true);
    expect(requiresQrBlock("INDIVIDUAL_DIPLOMA")).toBe(true);
  });

  it("never requires it on a thank-you letter, which may not carry one at all", () => {
    expect(requiresQrBlock("THANK_YOU")).toBe(false);
    expect(allowsFieldType("THANK_YOU", "qr_block")).toBe(false);
  });

  it("forces nothing onto a kind this build does not know", () => {
    // A required block the backend would then reject is worse than an absent one.
    expect(requiresQrBlock("CERTIFICATE")).toBe(false);
  });

  it("only requires what the kind is allowed to carry", () => {
    for (const type of ["DIPLOMA", "INDIVIDUAL_DIPLOMA", "THANK_YOU"]) {
      if (requiresQrBlock(type)) {
        expect(allowsFieldType(type, "qr_block")).toBe(true);
      }
    }
  });
});
