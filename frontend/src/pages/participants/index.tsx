/**
 * Participants page (placeholder).
 *
 * Bootstrap scope: layout skeleton only. The participants table (TanStack
 * Table) and management flows are delivered by the Participants feature. Minor
 * PII is never listed by identity — participants are addressed by opaque ids
 * (API-000 §10.3).
 */
export function ParticipantsPage(): React.JSX.Element {
  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-bold text-2xl tracking-tight">Участники</h1>
        <p className="text-muted-foreground text-sm">Список участников и управление ими.</p>
      </header>

      <div className="rounded-xl border bg-card p-6 shadow-elevation-1">
        <p className="text-muted-foreground text-sm">Таблица участников появится здесь.</p>
      </div>
    </section>
  );
}
