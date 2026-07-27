import { formatCompetitionDate } from "./format";
import type { VerifiedDiploma } from "./types";

/** Shown in place of a degree that no jury has awarded yet. */
export const DEGREE_PENDING_LABEL = "Результаты фестиваля ещё не опубликованы";

/**
 * How a value should read.
 *
 * `identifier` — an exact registry number, set in tabular mono so every character
 * is unambiguous. `award` — the conferred degree, the one fact worth emphasis.
 * `pending` — stands in for a result that does not exist yet, so the UI renders it
 * as secondary rather than as a printed fact.
 */
export type DiplomaFactKind = "text" | "identifier" | "award" | "pending";

/** One label/value line of the registry entry. */
export interface DiplomaFactRow {
  /** Stable key — also the field it came from. */
  key: string;
  label: string;
  /** Already-resolved display text. */
  value: string;
  kind: DiplomaFactKind;
}

/**
 * The registry entry's fact rows, in the order a diploma prints them.
 *
 * A row is omitted when its snapshot value is absent — a registry entry never
 * shows an empty "Организация" line, exactly as the printed diploma never draws a
 * field it has no value for. The one exception is **Степень**, which is always
 * shown: when the degree is null the row reports that results are not published
 * yet, which is a fact about the competition's progress rather than missing data.
 */
export function diplomaFactRows(diploma: VerifiedDiploma): DiplomaFactRow[] {
  const optional: Array<
    [key: string, label: string, value: string | null | undefined, kind: DiplomaFactKind]
  > = [
    ["number", "Номер диплома", diploma.number, "identifier"],
    ["participantName", "Участник", diploma.participantName, "text"],
    ["competitionTitle", "Фестиваль", diploma.competitionTitle, "text"],
    ["competitionDate", "Дата проведения", formatCompetitionDate(diploma.competitionDate), "text"],
    ["nomination", "Номинация", diploma.nomination, "text"],
    ["performance", "Произведение", diploma.performance, "text"],
    ["teacher", "Педагог", diploma.teacher, "text"],
    ["organization", "Организация", diploma.organization, "text"],
  ];

  const rows: DiplomaFactRow[] = [];
  for (const [key, label, value, kind] of optional) {
    const text = value?.trim();
    if (text) {
      rows.push({ key, label, value: text, kind });
    }
  }

  const degree = diploma.degree?.trim();
  rows.push({
    key: "degree",
    label: "Степень",
    value: degree || DEGREE_PENDING_LABEL,
    kind: degree ? "award" : "pending",
  });
  return rows;
}
