/**
 * Admission-rule cascade for the Performance Builder.
 *
 * Pure functions over the Registration Projection's `admissionRules`: they decide
 * which options are *selectable* at each step so the form never shows an invalid
 * combination. Nothing here talks to the network or the DOM.
 */
import type { RegistrationAdmissionRule } from "@/shared/api/generated/model-public-catalog";

export type PerformanceAxis =
  | "nominationId"
  | "disciplineId"
  | "ageCategoryId"
  | "participantGroupId"
  | "participationFormatId";

/**
 * The five configuration axes of a performance, in cascade order.
 *
 * The participant group (состав) comes before the age category because age
 * categories belong to a group: choosing the composition narrows which age
 * bands apply.
 */
export const PERFORMANCE_AXES: readonly PerformanceAxis[] = [
  "nominationId",
  "disciplineId",
  "participantGroupId",
  "ageCategoryId",
  "participationFormatId",
];

export type PerformanceSelection = Partial<Record<PerformanceAxis, string>>;

/** Whether ``rule`` matches every axis that is set in ``selection``. */
function ruleMatches(rule: RegistrationAdmissionRule, selection: PerformanceSelection): boolean {
  return PERFORMANCE_AXES.every((axis) => {
    const chosen = selection[axis];
    return chosen === undefined || rule[axis] === chosen;
  });
}

/**
 * The set of values ``axis`` may take given the other selected axes.
 *
 * ``axis`` itself is ignored in the match, so this answers "which options keep at
 * least one admission rule reachable". Downstream axes should be cleared when an
 * upstream axis changes (see :func:`clearDownstream`) so they never over-constrain.
 */
export function admissibleValues(
  rules: readonly RegistrationAdmissionRule[],
  selection: PerformanceSelection,
  axis: PerformanceAxis,
): Set<string> {
  const upstream: PerformanceSelection = { ...selection };
  delete upstream[axis];
  const values = new Set<string>();
  for (const rule of rules) {
    if (ruleMatches(rule, upstream)) {
      values.add(rule[axis]);
    }
  }
  return values;
}

/** Clear every axis after ``changed`` in cascade order (they depend on it). */
export function clearDownstream(
  selection: PerformanceSelection,
  changed: PerformanceAxis,
): PerformanceSelection {
  const index = PERFORMANCE_AXES.indexOf(changed);
  const next: PerformanceSelection = { ...selection };
  for (const axis of PERFORMANCE_AXES.slice(index + 1)) {
    delete next[axis];
  }
  return next;
}

/** Whether every axis is chosen and the full combination is covered by a rule. */
export function isFullyAdmissible(
  rules: readonly RegistrationAdmissionRule[],
  selection: PerformanceSelection,
): boolean {
  if (!PERFORMANCE_AXES.every((axis) => selection[axis] !== undefined)) {
    return false;
  }
  return rules.some((rule) => ruleMatches(rule, selection));
}

/** Age in whole years at ``reference`` for an ISO ``birthDate`` (``""`` → null). */
export function ageInYears(birthDate: string, reference: Date): number | null {
  if (!birthDate) {
    return null;
  }
  const dob = new Date(birthDate);
  if (Number.isNaN(dob.getTime())) {
    return null;
  }
  let age = reference.getFullYear() - dob.getFullYear();
  const beforeBirthday =
    reference.getMonth() < dob.getMonth() ||
    (reference.getMonth() === dob.getMonth() && reference.getDate() < dob.getDate());
  if (beforeBirthday) {
    age -= 1;
  }
  return age;
}

type MixedBand = { id: string; type?: string };

/**
 * Whether the chosen age category is a mixed one, and so leaves the ages of the
 * performers for the applicant to state.
 *
 * A mixed band ("смешанная") is deliberately open about who may enter it: the birth
 * dates on file describe the people listed, not the act, and only the applicant can
 * say that it is twelve children with two adults rather than the reverse. The backend
 * requires the answer before such a submission may be submitted.
 */
export function needsAgeComposition(
  ageCategories: readonly MixedBand[],
  ageCategoryId: string | undefined,
): boolean {
  if (!ageCategoryId) {
    return false;
  }
  return ageCategories.find((band) => band.id === ageCategoryId)?.type === "MIXED";
}

type AgeBand = { id: string; minAge: number; maxAge: number };

/** The age category whose band contains the participant's age, or ``undefined``. */
export function recommendedAgeCategoryId(
  ageCategories: readonly AgeBand[],
  birthDate: string,
  reference: Date,
): string | undefined {
  const age = ageInYears(birthDate, reference);
  if (age === null) {
    return undefined;
  }
  return ageCategories.find((band) => age >= band.minAge && age <= band.maxAge)?.id;
}
