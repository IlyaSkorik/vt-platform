import type {
  _AdmissionRule,
  _AgeCategory,
  _Category,
  _Discipline,
  _ParticipantGroup,
  _ParticipationFormat,
  AddAdmissionRule,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { formatAgeRangeLabel } from "./age-categories";
import { formatParticipantRange } from "./participant-groups";

export type AdmissionRuleKey = string;

export interface AdmissionRuleDraft {
  categoryId: string;
  disciplineIds: string[];
  ageCategoryIds: string[];
  participantGroupIds: string[];
  participationFormatIds: string[];
}

export interface AdmissionRuleLabels {
  categoryName: string;
  disciplineName: string;
  ageCategoryName: string;
  participantGroupName: string;
  participationFormatName: string;
}

export interface AdmissionRuleFilters {
  categoryId: string | null;
  disciplineId: string | null;
  ageCategoryId: string | null;
  participantGroupId: string | null;
  participationFormatId: string | null;
}

export interface AdmissionCoverageWarning {
  id: string;
  kind: "nomination" | "discipline" | "participant-group" | "format";
  message: string;
  sectionId?: "categories" | "age-categories" | "participant-groups" | "participation-formats";
}

export interface AdmissionRulesStats {
  totalRules: number;
  totalCombinationsPreview: number;
  disciplineCoveragePercent: number;
  disciplinesWithRules: number;
  disciplinesTotal: number;
  nominationsWithRules: number;
  nominationsTotal: number;
}

export interface BulkCreatePlan {
  toCreate: AddAdmissionRule[];
  skippedExisting: number;
  totalRequested: number;
}

export interface AdmissionLookupMaps {
  categories: Map<string, _Category>;
  disciplines: Map<string, _Discipline>;
  ageCategories: Map<string, _AgeCategory>;
  participantGroups: Map<string, _ParticipantGroup>;
  formats: Map<string, _ParticipationFormat>;
  existingKeys: Set<AdmissionRuleKey>;
}

export function admissionRuleKey(rule: {
  categoryId: string;
  disciplineId: string;
  ageCategoryId: string;
  participantGroupId: string;
  participationFormatId: string;
}): AdmissionRuleKey {
  return [
    rule.categoryId,
    rule.disciplineId,
    rule.ageCategoryId,
    rule.participantGroupId,
    rule.participationFormatId,
  ].join("|");
}

export function buildAdmissionLookupMaps(competition: CompetitionDetail): AdmissionLookupMaps {
  return {
    categories: new Map(competition.categories.map((item) => [item.id, item])),
    disciplines: new Map(competition.disciplines.map((item) => [item.id, item])),
    ageCategories: new Map(competition.ageCategories.map((item) => [item.id, item])),
    participantGroups: new Map(competition.participantGroups.map((item) => [item.id, item])),
    formats: new Map(competition.participationFormats.map((item) => [item.id, item])),
    existingKeys: new Set(competition.admissionRules.map((rule) => admissionRuleKey(rule))),
  };
}

export function resolveAdmissionRuleLabels(
  rule: _AdmissionRule,
  maps: AdmissionLookupMaps,
): AdmissionRuleLabels {
  const age = maps.ageCategories.get(rule.ageCategoryId);
  const group = maps.participantGroups.get(rule.participantGroupId);
  return {
    categoryName: maps.categories.get(rule.categoryId)?.name ?? "—",
    disciplineName: maps.disciplines.get(rule.disciplineId)?.name ?? "—",
    ageCategoryName: age ? `${age.name} (${formatAgeRangeLabel(age.minAge, age.maxAge)})` : "—",
    participantGroupName: group
      ? `${group.name} (${formatParticipantRange(group.minCount, group.maxCount)})`
      : "—",
    participationFormatName: maps.formats.get(rule.participationFormatId)?.name ?? "—",
  };
}

export function emptyAdmissionRuleDraft(): AdmissionRuleDraft {
  return {
    categoryId: "",
    disciplineIds: [],
    ageCategoryIds: [],
    participantGroupIds: [],
    participationFormatIds: [],
  };
}

export function draftFromRule(rule: _AdmissionRule): AdmissionRuleDraft {
  return {
    categoryId: rule.categoryId,
    disciplineIds: [rule.disciplineId],
    ageCategoryIds: [rule.ageCategoryId],
    participantGroupIds: [rule.participantGroupId],
    participationFormatIds: [rule.participationFormatId],
  };
}

/**
 * Age categories now belong to a participant group, so a (group, age) pair is only
 * valid when the age category belongs to that group. When ``ageGroupOf`` (a map of
 * ageCategoryId → participantGroupId) is provided, invalid pairs are excluded from
 * counts and plans; otherwise the full cartesian product is used.
 */
export function cartesianCount(
  draft: AdmissionRuleDraft,
  ageGroupOf?: ReadonlyMap<string, string>,
): number {
  const disciplines = Math.max(draft.disciplineIds.length, 0);
  const formats = Math.max(draft.participationFormatIds.length, 0);
  let groupAgePairs = 0;
  if (ageGroupOf) {
    for (const participantGroupId of draft.participantGroupIds) {
      for (const ageCategoryId of draft.ageCategoryIds) {
        if (ageGroupOf.get(ageCategoryId) === participantGroupId) {
          groupAgePairs += 1;
        }
      }
    }
  } else {
    groupAgePairs = draft.participantGroupIds.length * draft.ageCategoryIds.length;
  }
  if (disciplines === 0 || groupAgePairs === 0 || formats === 0) {
    return 0;
  }
  return disciplines * groupAgePairs * formats;
}

/** Expand builder selection into combinations; skip ones that already exist. */
export function planBulkAdmissionRules(
  draft: AdmissionRuleDraft,
  existingKeys: Set<AdmissionRuleKey>,
  ageGroupOf?: ReadonlyMap<string, string>,
): BulkCreatePlan {
  const toCreate: AddAdmissionRule[] = [];
  let skippedExisting = 0;
  let totalRequested = 0;

  if (!draft.categoryId) {
    return { toCreate, skippedExisting, totalRequested };
  }

  for (const disciplineId of draft.disciplineIds) {
    for (const ageCategoryId of draft.ageCategoryIds) {
      for (const participantGroupId of draft.participantGroupIds) {
        // Skip (group, age) pairs the backend would reject: the age category must
        // belong to the stated participant group.
        if (ageGroupOf && ageGroupOf.get(ageCategoryId) !== participantGroupId) {
          continue;
        }
        for (const participationFormatId of draft.participationFormatIds) {
          totalRequested += 1;
          const payload: AddAdmissionRule = {
            categoryId: draft.categoryId,
            disciplineId,
            ageCategoryId,
            participantGroupId,
            participationFormatId,
          };
          if (existingKeys.has(admissionRuleKey(payload))) {
            skippedExisting += 1;
            continue;
          }
          toCreate.push(payload);
        }
      }
    }
  }

  return { toCreate, skippedExisting, totalRequested };
}

/** Map ageCategoryId → participantGroupId for the whole competition. */
export function ageCategoryGroupMap(competition: CompetitionDetail): Map<string, string> {
  return new Map(competition.ageCategories.map((item) => [item.id, item.participantGroupId]));
}

export function emptyAdmissionFilters(): AdmissionRuleFilters {
  return {
    categoryId: null,
    disciplineId: null,
    ageCategoryId: null,
    participantGroupId: null,
    participationFormatId: null,
  };
}

export function filterAdmissionRules(
  rules: _AdmissionRule[],
  filters: AdmissionRuleFilters,
  search: string,
  maps: AdmissionLookupMaps,
): _AdmissionRule[] {
  const query = search.trim().toLowerCase();

  return rules.filter((rule) => {
    if (filters.categoryId && rule.categoryId !== filters.categoryId) return false;
    if (filters.disciplineId && rule.disciplineId !== filters.disciplineId) return false;
    if (filters.ageCategoryId && rule.ageCategoryId !== filters.ageCategoryId) return false;
    if (filters.participantGroupId && rule.participantGroupId !== filters.participantGroupId) {
      return false;
    }
    if (
      filters.participationFormatId &&
      rule.participationFormatId !== filters.participationFormatId
    ) {
      return false;
    }
    if (query.length === 0) return true;
    const labels = resolveAdmissionRuleLabels(rule, maps);
    const haystack =
      `${labels.categoryName} ${labels.disciplineName} ${labels.ageCategoryName} ${labels.participantGroupName} ${labels.participationFormatName}`.toLowerCase();
    return haystack.includes(query);
  });
}

export function sortAdmissionRules(
  rules: _AdmissionRule[],
  maps: AdmissionLookupMaps,
): _AdmissionRule[] {
  return [...rules].sort((left, right) => {
    const leftLabels = resolveAdmissionRuleLabels(left, maps);
    const rightLabels = resolveAdmissionRuleLabels(right, maps);
    return (
      leftLabels.categoryName.localeCompare(rightLabels.categoryName, "ru") ||
      leftLabels.disciplineName.localeCompare(rightLabels.disciplineName, "ru") ||
      leftLabels.ageCategoryName.localeCompare(rightLabels.ageCategoryName, "ru") ||
      leftLabels.participantGroupName.localeCompare(rightLabels.participantGroupName, "ru") ||
      leftLabels.participationFormatName.localeCompare(rightLabels.participationFormatName, "ru")
    );
  });
}

export function buildAdmissionCoverageWarnings(
  competition: CompetitionDetail,
): AdmissionCoverageWarning[] {
  const warnings: AdmissionCoverageWarning[] = [];
  const usedCategories = new Set(competition.admissionRules.map((rule) => rule.categoryId));
  const usedDisciplines = new Set(competition.admissionRules.map((rule) => rule.disciplineId));
  const usedGroups = new Set(competition.admissionRules.map((rule) => rule.participantGroupId));
  const usedFormats = new Set(competition.admissionRules.map((rule) => rule.participationFormatId));

  for (const category of competition.categories) {
    if (!usedCategories.has(category.id)) {
      warnings.push({
        id: `nomination-${category.id}`,
        kind: "nomination",
        message: `Жанр «${category.name}» не используется ни в одном правиле допуска.`,
        sectionId: "categories",
      });
    }
  }

  for (const discipline of competition.disciplines) {
    if (!usedDisciplines.has(discipline.id)) {
      const nomination = competition.categories.find((item) => item.id === discipline.categoryId);
      warnings.push({
        id: `discipline-${discipline.id}`,
        kind: "discipline",
        message: `Номинация «${discipline.name}»${
          nomination ? ` (${nomination.name})` : ""
        } не имеет правил допуска.`,
        sectionId: "categories",
      });
    }
  }

  for (const group of competition.participantGroups) {
    if (!usedGroups.has(group.id)) {
      warnings.push({
        id: `group-${group.id}`,
        kind: "participant-group",
        message: `Группа участников «${group.name}» нигде не используется.`,
        sectionId: "participant-groups",
      });
    }
  }

  for (const format of competition.participationFormats.filter((item) => item.enabled)) {
    if (!usedFormats.has(format.id)) {
      warnings.push({
        id: `format-${format.id}`,
        kind: "format",
        message: `Формат «${format.name}» включён, но не используется в правилах.`,
        sectionId: "participation-formats",
      });
    }
  }

  return warnings;
}

export function buildAdmissionRulesStats(
  competition: CompetitionDetail,
  draftPreviewCount = 0,
): AdmissionRulesStats {
  const usedDisciplines = new Set(competition.admissionRules.map((rule) => rule.disciplineId));
  const usedNominations = new Set(competition.admissionRules.map((rule) => rule.categoryId));
  const disciplinesTotal = competition.disciplines.length;
  const nominationsTotal = competition.categories.length;
  const disciplinesWithRules = usedDisciplines.size;
  const nominationsWithRules = usedNominations.size;

  return {
    totalRules: competition.admissionRules.length,
    totalCombinationsPreview: draftPreviewCount,
    disciplineCoveragePercent:
      disciplinesTotal === 0 ? 0 : Math.round((disciplinesWithRules / disciplinesTotal) * 100),
    disciplinesWithRules,
    disciplinesTotal,
    nominationsWithRules,
    nominationsTotal,
  };
}

export function scopedDisciplines(
  competition: CompetitionDetail,
  categoryId: string,
): _Discipline[] {
  return competition.disciplines
    .filter((item) => item.categoryId === categoryId)
    .slice()
    .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"));
}

/** Age categories belong to a participant group, so they are scoped by group. */
export function scopedAgeCategories(
  competition: CompetitionDetail,
  participantGroupId: string,
): _AgeCategory[] {
  return competition.ageCategories
    .filter((item) => item.participantGroupId === participantGroupId)
    .slice()
    .sort((a, b) => a.sortOrder - b.sortOrder || a.minAge - b.minAge);
}

/** Participant groups are competition-wide, so the full list is always in scope. */
export function allParticipantGroups(competition: CompetitionDetail): _ParticipantGroup[] {
  return competition.participantGroups
    .slice()
    .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"));
}

export function enabledParticipationFormats(
  competition: CompetitionDetail,
): _ParticipationFormat[] {
  return competition.participationFormats
    .filter((item) => item.enabled)
    .slice()
    .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"));
}

export function toggleId(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
}

export function canAdvanceBuilderStep(step: number, draft: AdmissionRuleDraft): boolean {
  switch (step) {
    case 1:
      return draft.categoryId.length > 0;
    case 2:
      return draft.disciplineIds.length > 0;
    // Groups are chosen before ages: age categories belong to a participant group.
    case 3:
      return draft.participantGroupIds.length > 0;
    case 4:
      return draft.ageCategoryIds.length > 0;
    case 5:
      return draft.participationFormatIds.length > 0;
    default:
      return true;
  }
}
