import type { VerifiedDiploma } from "./types";

/** Shown in place of a degree that no jury has awarded yet. */
export const DEGREE_PENDING_LABEL = "Результаты конкурса ещё не опубликованы";

/** One label/value line of the authenticity page. */
export interface DiplomaFactRow {
  /** Stable key — also the field it came from. */
  key: string;
  label: string;
  /** Already-resolved display text. */
  value: string;
  /**
   * True when `value` stands in for absent data rather than reporting it, so the
   * UI can render it as secondary/italic instead of as a printed fact.
   */
  pending?: boolean;
}

/**
 * The page's fact rows, in the order a diploma prints them.
 *
 * A row is omitted when its snapshot value is absent — a verification page never
 * shows an empty "Организация" line, exactly as the printed diploma never draws a
 * field it has no value for. The one exception is **Степень**, which is always
 * shown: when the degree is null the row reports that results are not published
 * yet, which is a fact about the competition's progress rather than missing data.
 */
export function diplomaFactRows(diploma: VerifiedDiploma): DiplomaFactRow[] {
  const optional: Array<[key: string, label: string, value: string | null | undefined]> = [
    ["number", "Номер", diploma.number],
    ["participantName", "Участник", diploma.participantName],
    ["competitionTitle", "Конкурс", diploma.competitionTitle],
    ["competitionDate", "Дата конкурса", diploma.competitionDate],
    ["nomination", "Номинация", diploma.nomination],
    ["performance", "Произведение", diploma.performance],
    ["teacher", "Педагог", diploma.teacher],
    ["organization", "Организация", diploma.organization],
  ];

  const rows: DiplomaFactRow[] = [];
  for (const [key, label, value] of optional) {
    const text = value?.trim();
    if (text) {
      rows.push({ key, label, value: text });
    }
  }

  const degree = diploma.degree?.trim();
  rows.push(
    degree
      ? { key: "degree", label: "Степень", value: degree }
      : { key: "degree", label: "Степень", value: DEGREE_PENDING_LABEL, pending: true },
  );
  return rows;
}
