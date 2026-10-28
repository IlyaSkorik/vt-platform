import { UserCircle2 } from "lucide-react";
import { Link, Outlet } from "react-router";
import { useAuth } from "@/app/providers";
import { APP_NAME, ROUTES } from "@/shared/config";
import { BrandMark, Button } from "@/shared/ui";
import { SiteFooter } from "./site-footer";
import { ThemeToggle } from "./theme-toggle";

/**
 * PublicLayout — chrome for unauthenticated, public-facing pages (landing,
 * public competition listings).
 *
 * A lightweight top bar (brand + theme + sign-in) over a full-width content
 * region and a simple footer. No sidebar: public pages are marketing-oriented,
 * not app surfaces.
 */
export function PublicLayout(): React.JSX.Element {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex min-h-svh flex-col bg-background">
      {/* The bar floats over the content the whole time it is on screen, and the hero
          it floats over is a photograph — so the separation is carried by a brand-tinted
          glow rather than by a grey line, which reads as a seam against an image. The
          border stays as the fallback where a hairline is all that is wanted. */}
      <header className="sticky top-0 z-[var(--z-sticky)] border-border border-b bg-background/90 shadow-glow-primary backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex h-16 w-full max-w-336 items-center justify-between gap-3 px-4 md:px-8">
          <div className="flex min-w-0 items-center gap-3 md:gap-5">
            <Link
              to={ROUTES.home}
              className="group inline-flex items-center gap-2 rounded-md pr-1 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {/* Keeps this header's own size, radius and hover lift — those were never
                  about the initials. The gradient is gone: it existed to give two flat
                  letters some depth, and behind an actual mark it only muddies the comet. */}
              <BrandMark className="size-9 rounded-lg shadow-sm transition-transform group-hover:scale-105" />
              <span className="truncate font-semibold text-foreground text-lg tracking-tight">
                {APP_NAME}
              </span>
            </Link>

            <nav aria-label="Публичная навигация" className="hidden items-center gap-1 md:flex">
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.home}>Главная</Link>
              </Button>
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.competitions}>Фестивали</Link>
              </Button>
              {/* The one entry here addressed to somebody who is not a participant.
                  It stays in the bar rather than only in the footer because an
                  organizer sent the link once will come back to the site, not to
                  the message. */}
              <Button asChild variant="ghost" size="sm">
                <Link to={ROUTES.organizers}>Организаторам</Link>
              </Button>
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <ThemeToggle />
            {isAuthenticated ? (
              <Button asChild iconOnly variant="ghost" size="sm" aria-label="Профиль">
                <Link to={ROUTES.cabinetProfile}>
                  <UserCircle2 className="size-5" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link to={ROUTES.login}>Войти</Link>
                </Button>
                <Button asChild size="sm" className="hidden sm:inline-flex">
                  <Link to={ROUTES.register}>Регистрация</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <SiteFooter />
    </div>
  );
}
