import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";
import { setCookieConsent } from "../model/consent-store";
import { useCookieConsent } from "../model/use-cookie-consent";

/**
 * The cookie decision bar.
 *
 * Shown until the visitor decides, then never again for a year. Three things about
 * it are legal requirements rather than design choices:
 *
 * - **Refusing is as easy as accepting** — both options are buttons of the same size,
 *   side by side, one click each. What matters legally is the effort, not the colour:
 *   the pattern regulators read as consent that was not freely given is a refusal
 *   hidden behind "manage preferences", not a refusal drawn in the secondary style.
 *   LEGAL-002 §2.3 therefore promises equal accessibility and placement, which is what
 *   this layout has to keep.
 * - **Nothing analytic runs while this is on screen.** The bar is the gate, not a
 *   notice: counters read `useAnalyticsConsent()`, which is `false` until a click.
 * - **No third state.** There is no dismiss control, because dismissing would be
 *   neither consent nor refusal, and LEGAL-002 §2.3 promises that closing the banner
 *   is not treated as consent. The bar is non-modal, so the site stays fully usable
 *   while it waits.
 */
export function CookieBanner(): React.JSX.Element | null {
  const consent = useCookieConsent();

  if (consent != null) {
    return null;
  }

  return (
    <section
      // A region rather than a dialog: it takes no focus and blocks nothing, which
      // is the honest shape for something that must not coerce a decision.
      aria-label="Использование файлов cookie"
      className="fixed inset-x-0 bottom-0 z-40 border-border border-t bg-background/95 px-4 py-4 shadow-elevation-2 backdrop-blur sm:px-6"
    >
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <p className="text-foreground/90 text-sm leading-6">
          На Платформе применяются строго необходимые файлы cookie, обеспечивающие аутентификацию и
          безопасность сеанса работы, а при наличии вашего согласия — аналитические файлы cookie
          сервисов «Яндекс Метрика» и Google Analytics. Отказ не ограничивает доступ к Платформе и
          её функциям.{" "}
          <Link to={ROUTES.cookiesPolicy} className="font-medium text-foreground underline">
            Политика использования файлов cookie
          </Link>
        </p>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
          {/* Refusal first and the same size as accepting: whichever style it carries,
              it costs the same one click and is never the option further away. */}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setCookieConsent(false);
            }}
          >
            Принять только необходимые
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setCookieConsent(true);
            }}
          >
            Принять все
          </Button>
        </div>
      </div>
    </section>
  );
}
