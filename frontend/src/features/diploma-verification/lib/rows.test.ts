import { describe, expect, it } from "vitest";
import { makeVerifiedDiploma } from "./fixtures";
import { DEGREE_PENDING_LABEL, diplomaFactRows } from "./rows";

describe("diplomaFactRows", () => {
  it("lists every fact in the order a diploma prints them", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma());
    expect(rows.map((row) => row.label)).toEqual([
      "Номер",
      "Участник",
      "Конкурс",
      "Дата конкурса",
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

  it("reports a pending result instead of dropping the degree row", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma({ degree: null }));
    const degree = rows.find((row) => row.key === "degree");
    expect(degree).toEqual({
      key: "degree",
      label: "Степень",
      value: DEGREE_PENDING_LABEL,
      pending: true,
    });
  });

  it("marks an awarded degree as a printed fact", () => {
    const rows = diplomaFactRows(makeVerifiedDiploma({ degree: "Гран-при" }));
    expect(rows.find((row) => row.key === "degree")).toEqual({
      key: "degree",
      label: "Степень",
      value: "Гран-при",
    });
  });
});
