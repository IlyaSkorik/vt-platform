/**
 * The two commercial terms an organization can be connected under, and the editing
 * model behind the per-performance one.
 *
 * The platform charges an organization either a share of the participation fees it
 * collects, or a flat price per submitted performance banded by how many
 * participants that performance has ("solo 2.50, up to five 4.00, larger 6.00").
 *
 * The backend requires those bands to cover every headcount: sorted, starting at
 * one participant, no gap, no overlap, open-ended at the top. Rather than let the
 * operator type a set of numbers that can violate all four, the editor here only
 * ever asks for each band's **upper bound** and price: the first band starts at one,
 * every next one starts where the previous ended, and the last is open-ended. A
 * gap or an overlap is then not something to validate — it is unrepresentable.
 *
 * Money is kept as a string end to end (see `platform-api`), so amounts are parsed
 * for validation and re-emitted as text, never held as a JavaScript number.
 */
import type { BillingModel, PerformanceFeeTier } from "@/applications/platform/api/platform-api";

/** The currency every fee is quoted in (the platform trades in one). */
export const FEE_CURRENCY = "BYN";

export const BILLING_MODEL_OPTIONS: { value: BillingModel; label: string }[] = [
  { value: "COMMISSION_PERCENT", label: "Процент от взносов" },
  { value: "PER_PERFORMANCE_FEE", label: "Фиксированная цена за номер" },
];

const BILLING_MODEL_LABELS: Record<BillingModel, string> = {
  COMMISSION_PERCENT: "Процент от взносов",
  PER_PERFORMANCE_FEE: "Цена за номер",
};

export function billingModelLabel(model: BillingModel): string {
  return BILLING_MODEL_LABELS[model] ?? model;
}

/**
 * One row of the editor: the band's upper bound and its price.
 *
 * `maxParticipants` of `null` marks the open-ended last row ("N и больше"); every
 * schedule has exactly one, and it is always last. The lower bound is never stored
 * — it is derived from the row above.
 */
export type FeeTierDraft = {
  id: string;
  maxParticipants: string;
  amount: string;
  openEnded: boolean;
};

function newId(): string {
  return crypto.randomUUID();
}

/** A fresh schedule: one open-ended band covering every performance. */
export function emptyFeeTierDrafts(): FeeTierDraft[] {
  return [{ id: newId(), maxParticipants: "", amount: "", openEnded: true }];
}

/** The saved schedule as editable rows (its last band is the open-ended one). */
export function feeTiersToDrafts(tiers: PerformanceFeeTier[]): FeeTierDraft[] {
  if (tiers.length === 0) {
    return emptyFeeTierDrafts();
  }
  return tiers.map((tier) => ({
    id: newId(),
    maxParticipants: tier.maxParticipants === null ? "" : String(tier.maxParticipants),
    amount: tier.amount,
    openEnded: tier.maxParticipants === null,
  }));
}

/** Where a row's band starts: one for the first, just past the row above for the rest. */
export function tierLowerBound(drafts: FeeTierDraft[], index: number): number {
  if (index === 0) {
    return 1;
  }
  const previous = Number.parseInt(drafts[index - 1]?.maxParticipants ?? "", 10);
  return Number.isNaN(previous) ? 1 : previous + 1;
}

/**
 * Add a band above the open-ended one, so the tail stays open.
 *
 * The new band's bound is seeded one past where it starts, i.e. the smallest range
 * it can cover — a value the operator can raise but never has to fix.
 */
export function addFeeTierDraft(drafts: FeeTierDraft[]): FeeTierDraft[] {
  const closed = drafts.slice(0, -1);
  const open = drafts.at(-1);
  const seed = tierLowerBound(drafts, closed.length);
  const inserted: FeeTierDraft = {
    id: newId(),
    maxParticipants: String(seed),
    amount: "",
    openEnded: false,
  };
  return open ? [...closed, inserted, open] : [inserted];
}

/** Drop one band. The open-ended one stays: without it a headcount would be unpriced. */
export function removeFeeTierDraft(drafts: FeeTierDraft[], id: string): FeeTierDraft[] {
  const remaining = drafts.filter((draft) => draft.id !== id || draft.openEnded);
  return remaining.length === 0 ? emptyFeeTierDrafts() : remaining;
}

/** `2.50` → `2.50`, `2,5` → `2.50`; anything that is not money at all → `null`. */
export function parseFeeAmount(value: string): string | null {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  return Number.parseFloat(normalized).toFixed(2);
}

/** `1` → `1 участник`, `2–5` → `2–5 участника`, `6+` → `от 6 участников`. */
export function formatTierRange(minParticipants: number, maxParticipants: number | null): string {
  if (maxParticipants === null) {
    return `от ${minParticipants} ${participantsWord(minParticipants)}`;
  }
  if (maxParticipants === minParticipants) {
    return `${minParticipants} ${participantsWord(minParticipants)}`;
  }
  return `${minParticipants}–${maxParticipants} ${participantsWord(maxParticipants)}`;
}

/** The band and its price on one line, the way the console lists saved terms. */
export function formatFeeTier(tier: PerformanceFeeTier): string {
  return `${formatTierRange(tier.minParticipants, tier.maxParticipants)} — ${tier.amount} ${FEE_CURRENCY}`;
}

function participantsWord(count: number): string {
  const tail = count % 100;
  if (tail >= 11 && tail <= 14) {
    return "участников";
  }
  switch (count % 10) {
    case 1:
      return "участник";
    case 2:
    case 3:
    case 4:
      return "участника";
    default:
      return "участников";
  }
}

export type FeeTierValidation = {
  /** Per-row messages, keyed by `<row id>.<field>`, as the form renders them. */
  errors: Record<string, string>;
  /** The payload to send, or `null` when anything is wrong. */
  tiers: PerformanceFeeTier[] | null;
};

/**
 * Turn the editor rows into the payload, or explain why they are not one yet.
 *
 * Only two things can be wrong, because the shape rules out the rest: a bound that
 * does not leave the band at least one participant wide, and a price that is not
 * money.
 */
export function validateFeeTiers(drafts: FeeTierDraft[]): FeeTierValidation {
  const errors: Record<string, string> = {};
  const tiers: PerformanceFeeTier[] = [];

  drafts.forEach((draft, index) => {
    const min = tierLowerBound(drafts, index);
    let max: number | null = null;
    let boundOk = true;
    if (!draft.openEnded) {
      const parsed = Number.parseInt(draft.maxParticipants.trim(), 10);
      if (Number.isNaN(parsed)) {
        errors[`${draft.id}.maxParticipants`] = "Укажите верхнюю границу";
        boundOk = false;
      } else if (parsed < min) {
        errors[`${draft.id}.maxParticipants`] = `Не меньше ${min}`;
        boundOk = false;
      } else {
        max = parsed;
      }
    }
    const amount = parseFeeAmount(draft.amount);
    if (amount === null) {
      errors[`${draft.id}.amount`] = "Цена вида 2.50";
    }
    if (boundOk && amount !== null) {
      tiers.push({ minParticipants: min, maxParticipants: max, amount });
    }
  });

  const complete = Object.keys(errors).length === 0 && tiers.length === drafts.length;
  return { errors, tiers: complete ? tiers : null };
}

/** Whether the rows say anything different from the schedule already saved. */
export function feeTiersEqual(left: PerformanceFeeTier[], right: PerformanceFeeTier[]): boolean {
  return (
    left.length === right.length &&
    left.every(
      (tier, index) =>
        tier.minParticipants === right[index]?.minParticipants &&
        tier.maxParticipants === right[index]?.maxParticipants &&
        tier.amount === right[index]?.amount,
    )
  );
}

/** What one order costs the platform under `tiers`, as an example the operator can read. */
export function exampleOrderTotal(tiers: PerformanceFeeTier[], headcounts: number[]): string {
  const total = headcounts.reduce((sum, count) => {
    const tier = tiers.find(
      (candidate) =>
        count >= candidate.minParticipants &&
        (candidate.maxParticipants === null || count <= candidate.maxParticipants),
    );
    return sum + (tier ? Number.parseFloat(tier.amount) : 0);
  }, 0);
  return total.toFixed(2);
}
