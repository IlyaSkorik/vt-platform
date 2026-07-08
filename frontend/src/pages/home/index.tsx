import { Link } from "react-router";
import { ThemeToggle } from "@/app/layouts/theme-toggle";
import { APP_NAME, ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

/**
 * Public landing page (placeholder).
 *
 * Bootstrap scope: layout and navigation entry points only. The marketing /
 * public competition listing content is added later.
 */
export function HomePage(): React.JSX.Element {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex items-center justify-between p-4">
        <span className="font-semibold text-lg tracking-tight">{APP_NAME}</span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="ghost">
            <Link to={ROUTES.login}>Войти</Link>
          </Button>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6 text-center">
        <div className="max-w-2xl space-y-4">
          <h1 className="text-balance font-bold text-4xl tracking-tight sm:text-5xl">
            Взлёт талантов
          </h1>
          <p className="text-pretty text-lg text-muted-foreground">
            Цифровая экосистема для организации детских творческих конкурсов — регистрация, подача
            работ, честное судейство и результаты в одном месте.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to={ROUTES.register}>Начать</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to={ROUTES.dashboard}>Перейти в панель</Link>
          </Button>
        </div>
      </main>
    </div>
  );
}
