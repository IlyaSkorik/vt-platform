/**
 * Profile page (placeholder).
 *
 * Bootstrap scope: layout skeleton only. Self-service profile editing
 * (`GET`/`PATCH /users/me`, API-001 §4.8) is delivered later.
 */
export function ProfilePage(): React.JSX.Element {
  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-bold text-2xl tracking-tight">Профиль</h1>
        <p className="text-muted-foreground text-sm">Управление аккаунтом и настройками.</p>
      </header>

      <div className="max-w-xl rounded-xl border bg-card p-6 shadow-elevation-1">
        <p className="text-muted-foreground text-sm">Настройки профиля появятся здесь.</p>
      </div>
    </section>
  );
}
