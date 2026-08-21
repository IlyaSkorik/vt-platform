import { CalendarClock } from "lucide-react";
import type { RegistrationNominationView } from "@/features/festival-landing";
import { Badge } from "@/shared/ui";
import { LandingSection } from "../landing-section";

interface RegistrationState {
  label: string;
  variant: "success" | "warning" | "secondary";
}

function formatInstant(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

function deriveState(nomination: RegistrationNominationView): RegistrationState {
  if (nomination.registrationStopped) {
    return { label: "Регистрация остановлена", variant: "warning" };
  }
  if (nomination.registrationOpen) {
    return {
      label: nomination.registrationClosesAt
        ? `Открыта до ${formatInstant(nomination.registrationClosesAt)}`
        : "Регистрация открыта",
      variant: "success",
    };
  }
  const now = Date.now();
  const opensMs = nomination.registrationOpensAt
    ? Date.parse(nomination.registrationOpensAt)
    : null;
  const closesMs = nomination.registrationClosesAt
    ? Date.parse(nomination.registrationClosesAt)
    : null;
  if (opensMs !== null && now < opensMs) {
    return {
      label: `Откроется ${formatInstant(nomination.registrationOpensAt)}`,
      variant: "secondary",
    };
  }
  if (closesMs !== null && now > closesMs) {
    return { label: "Регистрация завершена", variant: "secondary" };
  }
  return { label: "Регистрация ещё не открыта", variant: "secondary" };
}

function periodText(nomination: RegistrationNominationView): string {
  if (!nomination.registrationOpensAt && !nomination.registrationClosesAt) {
    return "Даты приёма заявок пока не назначены.";
  }
  return `Приём заявок: ${formatInstant(nomination.registrationOpensAt)} — ${formatInstant(nomination.registrationClosesAt)}`;
}

interface RegistrationBlockProps {
  nominations: RegistrationNominationView[];
}

/**
 * The registration block on the public landing: each nomination's application
 * window and current state (not yet open / open with dates / closed / stopped
 * early), so visitors see at a glance where they can still apply. Renders
 * nothing until at least one nomination exists.
 */
export function RegistrationBlock({
  nominations,
}: RegistrationBlockProps): React.JSX.Element | null {
  if (nominations.length === 0) {
    return null;
  }
  const sorted = [...nominations].sort(
    (a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name, "ru"),
  );
  return (
    <LandingSection id="registration" title="Регистрация">
      <ul className="grid gap-3 sm:grid-cols-2">
        {sorted.map((nomination) => {
          const state = deriveState(nomination);
          return (
            // The state badge never wraps ("Открыта до 20 июл. 2026 г., 23:00"
            // is ~230px on its own), so it only shares a row with the nomination
            // where the two-column grid is actually wide enough. Below that it
            // sits under the text instead of pushing the card off-screen.
            <li
              key={nomination.id}
              className="flex min-w-0 flex-col items-start gap-2 rounded-lg border bg-card p-4 text-card-foreground shadow-elevation-1 xl:flex-row xl:justify-between xl:gap-3"
            >
              <div className="flex min-w-0 items-start gap-3">
                <CalendarClock className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0 space-y-0.5">
                  <p className="font-medium break-words">{nomination.name}</p>
                  <p className="text-muted-foreground text-sm">{periodText(nomination)}</p>
                </div>
              </div>
              <Badge variant={state.variant} size="sm" className="max-w-full shrink-0">
                {state.label}
              </Badge>
            </li>
          );
        })}
      </ul>
    </LandingSection>
  );
}
