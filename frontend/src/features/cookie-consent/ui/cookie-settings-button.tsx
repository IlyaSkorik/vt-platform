import { resetCookieConsent } from "../model/consent-store";

/**
 * "Настройки cookie" — the way back to the decision, promised by LEGAL-002 §2.4.
 *
 * It clears the stored decision, which switches analytics off immediately and brings
 * the bar back so the visitor can choose again. Clearing rather than toggling is the
 * point: it works in both directions, and it never silently flips a choice the
 * visitor cannot see.
 *
 * Rendered as a plain text control so it can sit inside the footer's link list
 * without pretending to be a link — it performs an action, it does not navigate.
 */
export function CookieSettingsButton({ className }: { className?: string }): React.JSX.Element {
  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        resetCookieConsent();
      }}
    >
      Настройки cookie
    </button>
  );
}
