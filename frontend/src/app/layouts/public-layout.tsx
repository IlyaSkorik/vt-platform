import { UserCircle2 } from "lucide-react";
import { Link, Outlet } from "react-router";
import { useAuth } from "@/app/providers";
import { APP_NAME, ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";
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
  const entrepreneurName = "Скорик Илья Андреевич";
  const legalStatus = "Самозанятый";
  const unp = "УНП: ..";

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-[var(--z-sticky)] border-border border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex h-16 w-full max-w-336 items-center justify-between gap-3 px-4 md:px-8">
          <div className="flex min-w-0 items-center gap-3 md:gap-5">
            <Link
              to={ROUTES.home}
              className="group inline-flex items-center gap-2 rounded-md pr-1 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span
                aria-hidden="true"
                className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 font-extrabold text-primary-foreground text-sm shadow-sm transition-transform group-hover:scale-105"
              >
                ВТ
              </span>
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

      <footer className="border-border border-t bg-background/80 px-4 pt-8 pb-4 md:px-8">
        <div className="mx-auto grid w-full max-w-7xl gap-6 text-sm text-muted-foreground md:grid-cols-3">
          <div className="space-y-2">
            <p className="font-medium text-foreground">{APP_NAME}</p>
            <p>Платформа фестивалей и онлайн-подачи заявок.</p>
          </div>

          <div className="space-y-2">
            <p className="font-medium text-foreground">Документы</p>
            <div className="flex flex-col items-start gap-1">
              <Link to={ROUTES.privacyPolicy} className="hover:text-foreground hover:underline">
                Политика обработки персональных данных
              </Link>
              <Link to={ROUTES.cookiesPolicy} className="hover:text-foreground hover:underline">
                Политика обработки файлов cookies
              </Link>
            </div>
          </div>

          <div className="space-y-2">
            <p className="font-medium text-foreground">Реквизиты</p>
            <p>{entrepreneurName}</p>
            <p>{legalStatus}</p>
            <p>{unp}</p>
          </div>
        </div>
        <div className="mx-auto mt-6 w-full max-w-7xl border-border border-t pt-4 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} {APP_NAME}
        </div>
      </footer>
    </div>
  );
}
