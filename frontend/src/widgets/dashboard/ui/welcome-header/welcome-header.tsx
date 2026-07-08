import { Skeleton } from "@/shared/ui";

export interface WelcomeHeaderProps {
  /** The signed-in user's display name; when absent, a skeleton is shown. */
  userName?: string | undefined;
  /** Current time, injected for deterministic greeting in tests/stories. */
  now?: Date;
}

/** Time-of-day greeting in Russian, keyed off the local hour. */
function greetingFor(hour: number): string {
  if (hour < 6) {
    return "Доброй ночи";
  }
  if (hour < 12) {
    return "Доброе утро";
  }
  if (hour < 18) {
    return "Добрый день";
  }
  return "Добрый вечер";
}

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

/**
 * WelcomeHeader — the personalized greeting atop the dashboard.
 *
 * Renders a time-aware salutation, the user's name and today's date. While the
 * session name resolves, a compact skeleton stands in so the header never
 * jumps. Token-only, responsive typography.
 */
export function WelcomeHeader({
  userName,
  now = new Date(),
}: WelcomeHeaderProps): React.JSX.Element {
  const greeting = greetingFor(now.getHours());
  const date = dateFormatter.format(now);

  return (
    <div className="flex flex-col gap-1">
      {userName == null ? (
        <Skeleton className="h-8 w-64" />
      ) : (
        <h1 className="font-bold text-2xl text-foreground tracking-tight sm:text-3xl">
          {greeting}, {userName}
        </h1>
      )}
      <p className="text-muted-foreground text-sm first-letter:uppercase">{date}</p>
    </div>
  );
}
