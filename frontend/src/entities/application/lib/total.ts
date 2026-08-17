/**
 * How the order total is read out to the applicant.
 *
 * Pricing is optional per admission combination, so an order can legitimately carry
 * no sum at all — nothing in it was priced. That is not a blank to be filled in and
 * not a zero worth printing: what participation costs is then a question for the
 * festival's regulation, which is what {@link REGULATION_PRICE_NOTE} says. Screens
 * print the sum when there is one and the note when there is not.
 */
import type { _TotalPrice } from "@/shared/api/generated/model-applications";

/** Said where a sum would be, when the festival priced nothing that is in the order. */
export const REGULATION_PRICE_NOTE = "Стоимость определяется положением.";

/**
 * The order total as text, or `null` when there is nothing to charge for.
 *
 * A missing snapshot and a zero one mean the same thing to the applicant, so both
 * answer `null`.
 */
export function applicationTotalLabel(totalPrice: _TotalPrice | null | undefined): string | null {
  if (!totalPrice) return null;
  const amount = Number(totalPrice.totalAmount);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return `${totalPrice.totalAmount} ${totalPrice.currency}`;
}
