import { Link, NavLink, Outlet } from "react-router";
import { useAuth } from "@/app/providers";
import { APP_NAME, ROUTES } from "@/shared/config";
import { AccountCircleIcon, Button } from "@/shared/ui";
import { SiteFooter } from "./site-footer";
import { ThemeToggle } from "./theme-toggle";

/** The public navigation, in the order the Figma header lists it. */
const NAV_ITEMS = [
  { label: "Главная", to: ROUTES.home, end: true },
  { label: "Фестивали", to: ROUTES.competitions, end: false },
  // There is no standalone organiser page yet, so this points at the panel on
  // the landing that addresses them. A hash target rather than a dead route:
  // `ScrollRestoration` in the root layout takes the browser there from any
  // public page, and the day that content grows into a page of its own this
  // becomes a route change and nothing else moves.
  { label: "Организаторам", to: `${ROUTES.home}#for-organizers`, end: false },
] as const;

/**
 * PublicLayout — chrome for unauthenticated, public-facing pages (landing,
 * public competition listings).
 *
 * The bar is the brand's, not the application's: a solid `светлый акцент` band
 * carrying the mark and three links, set in the display face like everything
 * else on the public side. It does **not** float over the hero — the design
 * butts the artwork directly under it, and a translucent bar over an
 * illustration this pale only muddies both.
 *
 * Everything on the band — labels and both icons — is `--brand-mark`, the same
 * white the comet is drawn in, as the Figma frame has it. Noted once so it is
 * not "fixed" later: white on `светлый акцент` measures about 2.6:1 in the light
 * theme, under the 4.5:1 of WCAG 2.1 AA (ARCH-001 §8.3). This is the design's
 * call, kept deliberately; the dark theme's band is deep enough that the same
 * white clears AA there comfortably.
 */
export function PublicLayout(): React.JSX.Element {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-[var(--z-sticky)] bg-brand-surface font-heading text-brand-mark">
        <div className="mx-auto flex h-15 w-full max-w-336 items-center justify-between gap-3 px-4 md:px-8">
          <div className="flex min-w-0 items-center gap-6 md:gap-10">
            <Link
              to={ROUTES.home}
              aria-label={`${APP_NAME} — на главную`}
              className="shrink-0 rounded-sm outline-none transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-ring"
            >
              {/* Two pixels shy of the band top and bottom: `h-14` against the
                  bar's `h-15`. Flush looked like the mark had been cropped by
                  the header rather than placed in it. */}
              <img src="/logo-star.svg" alt="" width={48} height={55} className="h-14 w-auto" />
            </Link>

            {/* Noto Serif Bold 18/25 in `#FFFFFF`, from the frame: the face
                and weight come from the band, `leading-snug` is the 25px, and
                `--brand-mark` is that white.

                At night the frame lets them down to «свет полупрозрачный» —
                white at 70% — while the two icons stay at full strength; the
                band is deep enough there that the labels still clear AA.

                All three labels are the same tone, including the current one —
                the frame draws no active state at all, and the underline that
                used to mark it read as a seam across the bar. Nothing visual
                distinguishes the page you are on; `NavLink` still writes
                `aria-current="page"`, so assistive technology is told.

                Hover is a plate behind the label, not a change to the label:
                `свет` at 30% on a 6px corner — `--radius-sm` to the pixel. Its
                33px height is the 25px line plus `py-1`; the width follows the
                label, since the frame draws one rectangle per item rather than
                a fixed box. The items sit `gap-2` apart so the plates stay clear
                of each other without pushing the labels further apart than the
                bar has them. */}
            <nav
              aria-label="Публичная навигация"
              className="hidden items-center gap-2 font-bold text-lg leading-snug md:flex dark:text-on-scrim-muted"
            >
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.label}
                  to={item.to}
                  end={item.end}
                  className="rounded-sm px-4 py-1 outline-none transition-colors hover:bg-brand-mark/30 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-1 md:gap-2">
            <ThemeToggle className="size-11 text-brand-mark hover:bg-brand-mark/30 hover:text-brand-mark [&_svg]:size-[26px]" />
            {/* One icon, both states. The landing's own hero carries the signed-out
                call to action in full words; repeating it as a pair of buttons here
                is what the design dropped, and the icon still reaches the same
                place. */}
            <Button
              asChild
              iconOnly
              variant="ghost"
              size="md"
              aria-label={isAuthenticated ? "Личный кабинет" : "Войти"}
              // Sized here and not on the icon: the `size` variant carries
              // `[&_svg]:size-4`, a descendant selector that outranks a plain
              // class on the `svg` itself — set it there and nothing moves.
              className="size-11 text-brand-mark hover:bg-brand-mark/30 hover:text-brand-mark [&_svg]:size-[26px]"
            >
              <Link to={isAuthenticated ? ROUTES.cabinetProfile : ROUTES.login}>
                <AccountCircleIcon aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      {/* 250px tall on the public side, as the frame has it — the band is a
          closing gesture there, not the strip of fine print the workspace shells
          end on. Scoped to this layout for exactly that reason. */}
      <SiteFooter variant="brand" className="md:min-h-[250px]" />
    </div>
  );
}
