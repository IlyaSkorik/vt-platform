import { describe, expect, it } from "vitest";
import { FIELD_TYPES } from "./constructor";
import { allowsFieldType, documentTypeConfig } from "./document-types";

describe("allowsFieldType", () => {
  it("lets a diploma carry the whole catalogue", () => {
    for (const field of FIELD_TYPES) {
      expect(allowsFieldType("DIPLOMA", field.id)).toBe(true);
    }
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
    expect(documentTypeConfig("THANK_YOU").slotLabel).toBe("Шаблон благодарности");
  });

  it("falls back for a kind this build does not know", () => {
    expect(documentTypeConfig("CERTIFICATE").label).toBe("Документ");
  });
});
