import type { PublicFestivalPricing } from "@/shared/api/generated/model-public-catalog";

const priceFormatter = new Intl.NumberFormat("ru-RU", {
  maximumFractionDigits: 2,
});

/**
 * Format the "from X" starting-price summary, or `null` when no price is set.
 *
 * Mirrors the catalog card's price formatting but takes the pricing object
 * directly, so the landing feature stays decoupled from the catalog's `Festival`
 * shape.
 */
export function formatFromPrice(pricing: PublicFestivalPricing): string | null {
  if (pricing.amountFrom == null) {
    return null;
  }
  const numeric = Number(pricing.amountFrom);
  if (Number.isNaN(numeric)) {
    return null;
  }
  const amount = priceFormatter.format(numeric);
  const money = pricing.currency ? `${amount} ${pricing.currency}` : amount;
  return pricing.multiple ? `от ${money}` : money;
}
