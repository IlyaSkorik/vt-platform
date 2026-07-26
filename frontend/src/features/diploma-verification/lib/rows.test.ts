import { describe, expect, it } from "vitest";
import { makeVerifiedDiploma } from "./fixtures";
import { DEGREE_PENDING_LABEL, diplomaFactRows } from "./rows";

describe("diplomaFactRows", () => {
  it("lists every fact in the order a diploma prints them", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma());
    expect(rows.map((row) => row.label)).toEqual([
      "Номер диплома",
      "Участник",
      "Конкурс",
      "Дата проведения",
      "Номинация",
      "Произведение",
      "Педагог",
      "Организация",
      "Степень",
    ]);
  });

  it("omits a fact the snapshot does not carry", () => {
    const rows = diplomaFactRows(
      makeVerifiedDiploma({ organization: null, teacher: null, performance: "   " }),
    );
    const labels = rows.map((row) => row.label);
    // Absent values are dropped, not shown as an empty line.
    expect(labels).not.toContain("Организация");
    expect(labels).not.toContain("Педагог");
    expect(labels).not.toContain("Произведение");
    expect(labels).toContain("Участник");
  });

  it("marks the diploma number as an exact identifier", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma());
    expect(rows[0]).toEqual({
      key: "number",
      label: "Номер диплома",
      value: "VT-2026-000001",
      kind: "identifier",
    });
  });

  it("sets the competition date the way a document reads it", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma({ competitionDate: "12.04.2026" }));
    expect(rows.find((row) => row.key === "competitionDate")?.value).toBe("12 апреля 2026");
  });

  it("reports a pending result instead of dropping the degree row", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma({ degree: null }));
    expect(rows.find((row) => row.key === "degree")).toEqual({
      key: "degree",
      label: "Степень",
      value: DEGREE_PENDING_LABEL,
      kind: "pending",
    });
  });

  it("marks an awarded degree as the entry's one emphasised fact", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma({ degree: "Гран-при" }));
    expect(rows.find((row) => row.key === "degree")).toEqual({
      key: "degree",
      label: "Степень",
      value: "Гран-при",
      kind: "award",
    });
  });
});
