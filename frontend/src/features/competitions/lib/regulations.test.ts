import { describe, expect, it } from "vitest";
import type { _Regulation } from "@/shared/api/generated/model-competitions";
import {
  buildRegulationChangeLog,
  findCurrentRegulation,
  sortRegulationsNewestFirst,
  suggestNextRegulationVersion,
} from "./regulations";

function regulation(
  partial: Partial<_Regulation> & Pick<_Regulation, "id" | "version">,
): _Regulation {
  return {
    title: "Положение",
    publicationDate: "2026-01-01",
    fileReference: "/media/r.pdf",
    isCurrent: false,
    ...partial,
  };
}

describe("regulations helpers", () => {
  it("sorts newest publication date first", () => {
    const sorted = sortRegulationsNewestFirst([
      regulation({ id: "1", version: "1.0", publicationDate: "2026-01-01" }),
      regulation({ id: "2", version: "2.0", publicationDate: "2026-03-01" }),
      regulation({ id: "3", version: "1.5", publicationDate: "2026-02-01" }),
    ]);
    expect(sorted.map((item) => item.id)).toEqual(["2", "3", "1"]);
  });

  it("finds current regulation by id or flag", () => {
    const items = [
      regulation({ id: "1", version: "1.0", isCurrent: false }),
      regulation({ id: "2", version: "2.0", isCurrent: true }),
    ];
    expect(findCurrentRegulation(items, "1")?.id).toBe("1");
    expect(findCurrentRegulation(items, null)?.id).toBe("2");
  });

  it("suggests the next minor version", () => {
    expect(suggestNextRegulationVersion([])).toBe("1.0");
    expect(
      suggestNextRegulationVersion([
        regulation({ id: "1", version: "1.0", publicationDate: "2026-01-01" }),
        regulation({ id: "2", version: "2.3", publicationDate: "2026-02-01" }),
      ]),
    ).toBe("2.4");
  });

  it("builds a change log from published versions", () => {
    const log = buildRegulationChangeLog(
      [
        regulation({
          id: "2",
          version: "2.0",
          publicationDate: "2026-02-01",
          isCurrent: true,
        }),
        regulation({ id: "1", version: "1.0", publicationDate: "2026-01-01" }),
      ],
      { "2.0": "Уточнены сроки" },
    );
    expect(log).toHaveLength(2);
    expect(log[0]?.changeNote).toBe("Уточнены сроки");
    expect(log[0]?.summary).toContain("назначена текущей");
  });
});
