/**
 * Dashboard page (placeholder).
 *
 * Bootstrap scope: layout skeleton only. Real widgets (competition progress,
 * submissions, judging status) are composed here once those features exist.
 */
export function DashboardPage(): React.JSX.Element {
  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-bold text-2xl tracking-tight">Панель</h1>
        <p className="text-muted-foreground text-sm">Обзор вашей активности на платформе.</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {["Конкурсы", "Заявки", "Судейство"].map((title) => (
          <article
            key={title}
            className="rounded-xl border bg-card p-6 shadow-elevation-1"
            aria-label={title}
          >
            <h2 className="font-medium text-sm">{title}</h2>
            <p className="mt-2 text-muted-foreground text-sm">Данные появятся здесь.</p>
          </article>
        ))}
      </div>
    </section>
  );
}
