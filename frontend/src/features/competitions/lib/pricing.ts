import type {
  _AdmissionRule,
  _PricingRule,
  AddPricingRule,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import {
  type AdmissionLookupMaps,
  type AdmissionRuleKey,
  type AdmissionRuleLabels,
  admissionRuleKey,
  buildAdmissionLookupMaps,
  resolveAdmissionRuleLabels,
  sortAdmissionRules,
} from "./admission-rules";

export type PricingStatus = "configured" | "missing";

export interface PricingRow {
  key: AdmissionRuleKey;
  rule: _AdmissionRule;
  labels: AdmissionRuleLabels;
  price: _PricingRule | null;
  status: PricingStatus;
}

export interface PricingFilters {
  categoryId: string | null;
  disciplineId: string | null;
  ageCategoryId: string | null;
  participantGroupId: string | null;
  participationFormatId: string | null;
  /** null = all, configured = has price, missing = no price */
  priceStatus: PricingStatus | null;
}

export interface PricingStats {
  admissionRules: number;
  configuredPrices: number;
  missingPrices: number;
  completionPercent: number;
  averagePrice: number | null;
  lowestPrice: number | null;
  highestPrice: number | null;
  currency: string;
  perParticipantCount: number;
  perPerformanceCount: number;
}

export interface PricingWarning {
  id: string;
  kind: "missing-price" | "disabled-format-price" | "orphan-price";
  message: string;
  sectionId?: "admission-rules" | "participation-formats" | "pricing";
}

export type PricingCalculationTypeValue = "PER_PARTICIPANT" | "PER_PERFORMANCE";

export type BulkPriceOperation =
  | { type: "set"; amount: number }
  | { type: "increase-percent"; percent: number }
  | { type: "decrease-percent"; percent: number }
  | { type: "increase-amount"; amount: number }
  | { type: "decrease-amount"; amount: number }
  | { type: "set-calculation-type"; calculationType: PricingCalculationTypeValue }
  | { type: "remove" };

export type CopyPricingDimension = "format" | "group" | "age" | "nomination";

export interface CopyPricingPlanItem {
  target: _AdmissionRule;
  amount: string;
  currency: string;
  calculationType: PricingCalculationTypeValue;
  hadPrice: boolean;
}

export interface CopyPricingPlan {
  items: CopyPricingPlanItem[];
  skippedNoTarget: number;
  skippedNoSourcePrice: number;
}

export interface PricingMutationPayload {
  categoryId: string;
  disciplineId: string;
  ageCategoryId: string;
  participantGroupId: string;
  participationFormatId: string;
  amount: string;
  currency: string;
  calculationType: PricingCalculationTypeValue;
  mode: "add" | "change";
}

export const DEFAULT_CURRENCY = "BYN";
export const DEFAULT_CALCULATION_TYPE = "PER_PARTICIPANT" as const;

export const PRICING_CALCULATION_TYPE_OPTIONS: Array<{
  value: PricingCalculationTypeValue;
  label: string;
}> = [
  { value: "PER_PARTICIPANT", label: "За участника" },
  { value: "PER_PERFORMANCE", label: "За номер" },
];

export function calculationTypeLabel(value: string | null | undefined): string {
  if (value === "PER_PERFORMANCE") return "За номер";
  return "За участника";
}

export function normalizeCalculationType(
  value: string | null | undefined,
): PricingCalculationTypeValue {
  return value === "PER_PERFORMANCE" ? "PER_PERFORMANCE" : "PER_PARTICIPANT";
}

export function emptyPricingFilters(): PricingFilters {
  return {
    categoryId: null,
    disciplineId: null,
    ageCategoryId: null,
    participantGroupId: null,
    participationFormatId: null,
    priceStatus: null,
  };
}

export function buildPricingMap(
  competition: CompetitionDetail,
): Map<AdmissionRuleKey, _PricingRule> {
  return new Map(competition.pricingRules.map((rule) => [admissionRuleKey(rule), rule]));
}

export function buildPricingRows(
  competition: CompetitionDetail,
  maps: AdmissionLookupMaps = buildAdmissionLookupMaps(competition),
): PricingRow[] {
  const prices = buildPricingMap(competition);
  const rows = competition.admissionRules.map((rule) => {
    const price = prices.get(admissionRuleKey(rule)) ?? null;
    return {
      key: admissionRuleKey(rule),
      rule,
      labels: resolveAdmissionRuleLabels(rule, maps),
      price,
      status: price ? ("configured" as const) : ("missing" as const),
    };
  });
  return sortAdmissionRules(
    rows.map((row) => row.rule),
    maps,
  ).map((rule) => {
    const key = admissionRuleKey(rule);
    const price = prices.get(key) ?? null;
    return {
      key,
      rule,
      labels: resolveAdmissionRuleLabels(rule, maps),
      price,
      status: price ? ("configured" as const) : ("missing" as const),
    };
  });
}

export function filterPricingRows(
  rows: PricingRow[],
  filters: PricingFilters,
  search: string,
): PricingRow[] {
  const query = search.trim().toLowerCase();

  return rows.filter((row) => {
    if (filters.categoryId && row.rule.categoryId !== filters.categoryId) return false;
    if (filters.disciplineId && row.rule.disciplineId !== filters.disciplineId) return false;
    if (filters.ageCategoryId && row.rule.ageCategoryId !== filters.ageCategoryId) return false;
    if (filters.participantGroupId && row.rule.participantGroupId !== filters.participantGroupId) {
      return false;
    }
    if (
      filters.participationFormatId &&
      row.rule.participationFormatId !== filters.participationFormatId
    ) {
      return false;
    }
    if (filters.priceStatus && row.status !== filters.priceStatus) return false;
    if (query.length === 0) return true;
    const { labels, price } = row;
    const haystack =
      `${labels.categoryName} ${labels.disciplineName} ${labels.ageCategoryName} ${labels.participantGroupName} ${labels.participationFormatName} ${price?.amount ?? ""} ${price?.currency ?? ""}`.toLowerCase();
    return haystack.includes(query);
  });
}

export function parseAmount(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (normalized.length === 0) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null;
  const amount = Number(normalized);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return amount;
}

export function formatAmount(amount: number): string {
  return amount.toFixed(2);
}

export function applyBulkOperation(
  currentAmount: number | null,
  operation: BulkPriceOperation,
): number | null {
  if (operation.type === "remove") return null;
  if (operation.type === "set-calculation-type") {
    return currentAmount != null && currentAmount > 0 ? roundMoney(currentAmount) : null;
  }
  if (operation.type === "set") {
    return operation.amount > 0 ? roundMoney(operation.amount) : null;
  }
  if (currentAmount == null || currentAmount <= 0) return null;

  switch (operation.type) {
    case "increase-percent":
      return roundMoney(currentAmount * (1 + operation.percent / 100));
    case "decrease-percent":
      return roundMoney(currentAmount * (1 - operation.percent / 100));
    case "increase-amount":
      return roundMoney(currentAmount + operation.amount);
    case "decrease-amount":
      return roundMoney(currentAmount - operation.amount);
    default:
      return currentAmount;
  }
}

function roundMoney(amount: number): number | null {
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return Math.round(amount * 100) / 100;
}

export function planBulkPricingMutations(
  rows: PricingRow[],
  selectedKeys: Set<AdmissionRuleKey>,
  operation: BulkPriceOperation,
  currency = DEFAULT_CURRENCY,
): { upserts: PricingMutationPayload[]; removes: _AdmissionRule[] } {
  const upserts: PricingMutationPayload[] = [];
  const removes: _AdmissionRule[] = [];

  for (const row of rows) {
    if (!selectedKeys.has(row.key)) continue;

    if (operation.type === "set-calculation-type") {
      if (!row.price) continue;
      const currentType = normalizeCalculationType(row.price.calculationType);
      if (currentType === operation.calculationType) continue;
      const currentAmount = Number(row.price.amount);
      if (!Number.isFinite(currentAmount) || currentAmount <= 0) continue;
      upserts.push({
        categoryId: row.rule.categoryId,
        disciplineId: row.rule.disciplineId,
        ageCategoryId: row.rule.ageCategoryId,
        participantGroupId: row.rule.participantGroupId,
        participationFormatId: row.rule.participationFormatId,
        amount: formatAmount(currentAmount),
        currency: row.price.currency ?? currency,
        calculationType: operation.calculationType,
        mode: "change",
      });
      continue;
    }

    const current = row.price ? Number(row.price.amount) : null;
    const next = applyBulkOperation(
      current != null && Number.isFinite(current) ? current : null,
      operation,
    );

    if (operation.type === "remove" || next == null) {
      if (row.price) removes.push(row.rule);
      continue;
    }

    upserts.push({
      categoryId: row.rule.categoryId,
      disciplineId: row.rule.disciplineId,
      ageCategoryId: row.rule.ageCategoryId,
      participantGroupId: row.rule.participantGroupId,
      participationFormatId: row.rule.participationFormatId,
      amount: formatAmount(next),
      currency: row.price?.currency ?? currency,
      calculationType: normalizeCalculationType(row.price?.calculationType),
      mode: row.price ? "change" : "add",
    });
  }

  return { upserts, removes };
}

export function planTemplatePricing(
  rows: PricingRow[],
  selectedKeys: Set<AdmissionRuleKey>,
  amount: number,
  currency = DEFAULT_CURRENCY,
): PricingMutationPayload[] {
  return planBulkPricingMutations(rows, selectedKeys, { type: "set", amount }, currency).upserts;
}

/** Copy prices along one dimension for rules that share the other four. */
export function planCopyPricing(
  competition: CompetitionDetail,
  dimension: CopyPricingDimension,
  sourceId: string,
  targetId: string,
): CopyPricingPlan {
  if (sourceId === targetId) {
    return { items: [], skippedNoTarget: 0, skippedNoSourcePrice: 0 };
  }

  const prices = buildPricingMap(competition);
  const admissionKeys = new Set(competition.admissionRules.map((rule) => admissionRuleKey(rule)));
  const items: CopyPricingPlanItem[] = [];
  let skippedNoTarget = 0;
  let skippedNoSourcePrice = 0;

  if (dimension === "nomination") {
    return planCopyNominationPricing(competition, sourceId, targetId, prices, admissionKeys);
  }

  const field =
    dimension === "format"
      ? "participationFormatId"
      : dimension === "group"
        ? "participantGroupId"
        : "ageCategoryId";

  for (const rule of competition.admissionRules) {
    if (rule[field] !== sourceId) continue;
    const sourcePrice = prices.get(admissionRuleKey(rule));
    if (!sourcePrice) {
      skippedNoSourcePrice += 1;
      continue;
    }

    const targetRule: _AdmissionRule = { ...rule, [field]: targetId };
    const targetKey = admissionRuleKey(targetRule);
    if (!admissionKeys.has(targetKey)) {
      skippedNoTarget += 1;
      continue;
    }

    items.push({
      target: targetRule,
      amount: sourcePrice.amount,
      currency: sourcePrice.currency,
      calculationType: normalizeCalculationType(sourcePrice.calculationType),
      hadPrice: prices.has(targetKey),
    });
  }

  return { items, skippedNoTarget, skippedNoSourcePrice };
}

function planCopyNominationPricing(
  competition: CompetitionDetail,
  sourceCategoryId: string,
  targetCategoryId: string,
  prices: Map<AdmissionRuleKey, _PricingRule>,
  admissionKeys: Set<AdmissionRuleKey>,
): CopyPricingPlan {
  const maps = buildAdmissionLookupMaps(competition);
  const sourceRules = competition.admissionRules.filter(
    (rule) => rule.categoryId === sourceCategoryId,
  );
  const targetDisciplines = competition.disciplines.filter(
    (d) => d.categoryId === targetCategoryId,
  );
  // Age categories and participant groups are no longer scoped per nomination:
  // groups are competition-wide and ages belong to a group, so the whole list is
  // in scope and we match by name (as before) to line up source and target.
  const targetAges = competition.ageCategories;
  const targetGroups = competition.participantGroups;

  const disciplineByName = new Map(
    targetDisciplines.map((item) => [item.name.toLowerCase(), item.id]),
  );
  const ageByName = new Map(targetAges.map((item) => [item.name.toLowerCase(), item.id]));
  const groupByName = new Map(targetGroups.map((item) => [item.name.toLowerCase(), item.id]));

  const items: CopyPricingPlanItem[] = [];
  let skippedNoTarget = 0;
  let skippedNoSourcePrice = 0;

  for (const rule of sourceRules) {
    const sourcePrice = prices.get(admissionRuleKey(rule));
    if (!sourcePrice) {
      skippedNoSourcePrice += 1;
      continue;
    }

    const disciplineName = maps.disciplines.get(rule.disciplineId)?.name.toLowerCase();
    const ageName = maps.ageCategories.get(rule.ageCategoryId)?.name.toLowerCase();
    const groupName = maps.participantGroups.get(rule.participantGroupId)?.name.toLowerCase();
    if (!disciplineName || !ageName || !groupName) {
      skippedNoTarget += 1;
      continue;
    }

    const disciplineId = disciplineByName.get(disciplineName);
    const ageCategoryId = ageByName.get(ageName);
    const participantGroupId = groupByName.get(groupName);
    if (!disciplineId || !ageCategoryId || !participantGroupId) {
      skippedNoTarget += 1;
      continue;
    }

    const target: _AdmissionRule = {
      categoryId: targetCategoryId,
      disciplineId,
      ageCategoryId,
      participantGroupId,
      participationFormatId: rule.participationFormatId,
    };
    const targetKey = admissionRuleKey(target);
    if (!admissionKeys.has(targetKey)) {
      skippedNoTarget += 1;
      continue;
    }

    items.push({
      target,
      amount: sourcePrice.amount,
      currency: sourcePrice.currency,
      calculationType: normalizeCalculationType(sourcePrice.calculationType),
      hadPrice: prices.has(targetKey),
    });
  }

  return { items, skippedNoTarget, skippedNoSourcePrice };
}

export function copyPlanToMutations(plan: CopyPricingPlan): PricingMutationPayload[] {
  return plan.items.map((item) => ({
    categoryId: item.target.categoryId,
    disciplineId: item.target.disciplineId,
    ageCategoryId: item.target.ageCategoryId,
    participantGroupId: item.target.participantGroupId,
    participationFormatId: item.target.participationFormatId,
    amount: normalizeAmountString(item.amount),
    currency: item.currency || DEFAULT_CURRENCY,
    calculationType: item.calculationType,
    mode: item.hadPrice ? "change" : "add",
  }));
}

export function normalizeAmountString(amount: string): string {
  const parsed = parseAmount(amount);
  return parsed == null ? amount : formatAmount(parsed);
}

export function buildPricingStats(competition: CompetitionDetail): PricingStats {
  const rows = buildPricingRows(competition);
  const configured = rows.filter((row) => row.price != null);
  const amounts = configured
    .map((row) => Number(row.price?.amount))
    .filter((amount) => Number.isFinite(amount));
  const total = rows.length;
  const configuredCount = configured.length;
  const currency = configured[0]?.price?.currency ?? DEFAULT_CURRENCY;
  const perParticipantCount = configured.filter(
    (row) => normalizeCalculationType(row.price?.calculationType) === "PER_PARTICIPANT",
  ).length;
  const perPerformanceCount = configured.length - perParticipantCount;

  return {
    admissionRules: total,
    configuredPrices: configuredCount,
    missingPrices: total - configuredCount,
    completionPercent: total === 0 ? 0 : Math.round((configuredCount / total) * 100),
    averagePrice:
      amounts.length === 0
        ? null
        : Math.round((amounts.reduce((sum, amount) => sum + amount, 0) / amounts.length) * 100) /
          100,
    lowestPrice: amounts.length === 0 ? null : Math.min(...amounts),
    highestPrice: amounts.length === 0 ? null : Math.max(...amounts),
    currency,
    perParticipantCount,
    perPerformanceCount,
  };
}

export function buildPricingWarnings(competition: CompetitionDetail): PricingWarning[] {
  const warnings: PricingWarning[] = [];
  const prices = buildPricingMap(competition);
  const admissionKeys = new Set(competition.admissionRules.map((rule) => admissionRuleKey(rule)));
  const maps = buildAdmissionLookupMaps(competition);

  let missingCount = 0;
  for (const rule of competition.admissionRules) {
    if (!prices.has(admissionRuleKey(rule))) missingCount += 1;
  }
  if (missingCount > 0) {
    warnings.push({
      id: "missing-prices",
      kind: "missing-price",
      // Цены необязательны: комбинация без цены остаётся допустимой и просто ничего
      // не добавляет к сумме заявки. Публикации это не мешает.
      message: `${missingCount} правил допуска без цены — участие по ним не войдёт в сумму заявки.`,
      sectionId: "pricing",
    });
  }

  for (const price of competition.pricingRules) {
    const format = maps.formats.get(price.participationFormatId);
    if (format && !format.enabled) {
      warnings.push({
        id: `disabled-format-${admissionRuleKey(price)}`,
        kind: "disabled-format-price",
        message: `Цена задана для выключенного формата «${format.name}».`,
        sectionId: "participation-formats",
      });
    }
    if (!admissionKeys.has(admissionRuleKey(price))) {
      warnings.push({
        id: `orphan-${admissionRuleKey(price)}`,
        kind: "orphan-price",
        message: "Найдена цена без соответствующего правила допуска.",
        sectionId: "admission-rules",
      });
    }
  }

  return warnings;
}

export function toAddPricingPayload(payload: PricingMutationPayload): AddPricingRule {
  return {
    categoryId: payload.categoryId,
    disciplineId: payload.disciplineId,
    ageCategoryId: payload.ageCategoryId,
    participantGroupId: payload.participantGroupId,
    participationFormatId: payload.participationFormatId,
    amount: payload.amount,
    currency: payload.currency,
    calculationType: payload.calculationType,
  };
}

export function optimisticPricingDetail(
  competition: CompetitionDetail,
  upserts: PricingMutationPayload[],
  removes: Array<{
    categoryId: string;
    disciplineId: string;
    ageCategoryId: string;
    participantGroupId: string;
    participationFormatId: string;
  }> = [],
): CompetitionDetail {
  const map = buildPricingMap(competition);
  for (const remove of removes) {
    map.delete(admissionRuleKey(remove));
  }
  for (const upsert of upserts) {
    map.set(admissionRuleKey(upsert), {
      categoryId: upsert.categoryId,
      disciplineId: upsert.disciplineId,
      ageCategoryId: upsert.ageCategoryId,
      participantGroupId: upsert.participantGroupId,
      participationFormatId: upsert.participationFormatId,
      amount: upsert.amount,
      currency: upsert.currency,
      calculationType: upsert.calculationType,
    });
  }
  return {
    ...competition,
    pricingRules: [...map.values()],
  };
}

export function exampleTotalCost(
  unitPrice: number,
  participantCount: number,
  calculationType: PricingCalculationTypeValue = "PER_PARTICIPANT",
): string {
  if (calculationType === "PER_PERFORMANCE") {
    return formatAmount(unitPrice);
  }
  return formatAmount(unitPrice * participantCount);
}

export function calculateApplicationTotal(
  unitPrice: number,
  participantCount: number,
  calculationType: PricingCalculationTypeValue = "PER_PARTICIPANT",
): number {
  if (calculationType === "PER_PERFORMANCE") {
    return roundMoney(unitPrice) ?? 0;
  }
  return roundMoney(unitPrice * participantCount) ?? 0;
}
