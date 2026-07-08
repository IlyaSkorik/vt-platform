import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

/**
 * Public landing page (placeholder).
 *
 * Renders inside `PublicLayout`, which owns the top bar and footer, so this
 * page contributes the hero content only. Marketing / public competition
 * listings are added later.
 */
export function HomePage(): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-6 px-6 py-24 text-center">
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
    </div>
  );
}
