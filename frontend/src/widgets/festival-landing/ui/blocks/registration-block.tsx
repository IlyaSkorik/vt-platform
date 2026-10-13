import type { RegistrationNominationView } from "@/features/festival-landing";
import { cn } from "@/shared/lib";
import { CalendarClockIcon } from "@/shared/ui";
import { LandingSection } from "../landing-section";

type IntakeTone = "open" | "closed" | "soon";

interface IntakeState {
  label: string;
  tone: IntakeTone;
}

/**
 * `03.09.2026 18:00` — the frame's own format, and the one the organiser typed
 * into the builder. `toLocaleString`'s medium style («3 сент. 2026 г., 18:00»)
 * is the application chrome's voice and runs half again as long, which matters
 * when two of these share a row.
 */
function formatInstant(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const pad = (value: number): string => String(value).padStart(2, "0");
  return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Which of the three plates a nomination wears.
 *
 * One word each, as the frame draws them. The long sentences this used to
 * print («Открыта до 20 июл. 2026 г., 23:00») said twice over what the dates
 * directly underneath already say, and at ~230px the chip could not share a
 * row with the nomination's name.
 *
 * An intake the organiser stopped early is its own case and keeps its own
 * word: it is closed, but not because a deadline passed, and a visitor who
 * checked yesterday deserves to see that the difference is deliberate.
 */
function deriveState(nomination: RegistrationNominationView): IntakeState {
  if (nomination.registrationStopped) {
    return { label: "остановлена", tone: "closed" };
  }
  if (nomination.registrationOpen) {
    return { label: "открыта", tone: "open" };
  }
  const now = Date.now();
  const opensMs = nomination.registrationOpensAt
    ? Date.parse(nomination.registrationOpensAt)
    : null;
  if (opensMs !== null && now < opensMs) {
    return { label: "скоро откроется", tone: "soon" };
  }
  const closesMs = nomination.registrationClosesAt
    ? Date.parse(nomination.registrationClosesAt)
    : null;
  if (closesMs !== null && now > closesMs) {
    return { label: "закрыта", tone: "closed" };
  }
  return { label: "скоро откроется", tone: "soon" };
}

const INTAKE_TONES: Record<IntakeTone, string> = {
  open: "border-intake-open-line bg-intake-open",
  closed: "border-intake-closed-line bg-intake-closed",
  soon: "border-intake-soon-line bg-intake-soon",
};

/**
 * The state plate: a pastel rectangle on the brand's 15px corner with «Темный
 * текст» on it, not one of the `Badge` status variants.
 *
 * `Badge` colours the *text* with the status and leaves the fill a tint, and it
 * is a full-round pill — the application chrome's language, for a warning you
 * are meant to notice. Here the plate carries the colour and the label stays
 * dark, so three of these down a column read as labels on a panel.
 *
 * At night the chip turns inside out — a hairline with a tenth of its colour
 * behind it — and the border is always drawn, because by day the line is the
 * plate's own colour and reads as no line at all. The theme owns which of the
 * two it is; this component just draws a bordered chip.
 */
function IntakeChip({ state }: { state: IntakeState }): React.JSX.Element {
  return (
    <span
      className={cn(
        "inline-flex h-[19px] shrink-0 items-center rounded-brand border px-3 text-intake-foreground text-[10px] leading-[14px] md:h-6 md:text-sm md:leading-[19px]",
        INTAKE_TONES[state.tone],
      )}
    >
      {state.label}
    </span>
  );
}

interface RegistrationBlockProps {
  nominations: RegistrationNominationView[];
}

/**
 * «Регистрация» — one card per nomination: its name, its application window and
 * the state of that window right now, so a visitor sees at a glance where they
 * can still apply. Renders nothing until at least one nomination exists.
 *
 * Three lines when the organizer has filled them in: the name with its state,
 * the intake window, and the date the nomination is actually performed. That
 * last one is the nomination's own — a festival running over several days
 * judges one genre a day, so "when do I perform" has no answer at the
 * competition level — and it is absent from the card when nobody set it,
 * rather than falling back to the festival's start date. One number repeated
 * down the column is not a per-nomination fact.
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
      {/* 4px between cards, as the frame measures it: the list is one block of
          nominations rather than a set of separate panels. */}
      <ul className="space-y-1.5 md:space-y-1">
        {sorted.map((nomination) => {
          const state = deriveState(nomination);
          const opens = formatInstant(nomination.registrationOpensAt);
          const closes = formatInstant(nomination.registrationClosesAt);
          const held = formatInstant(nomination.heldAt);
          return (
            // 19px, the one corner on the page that is not the brand's 15 — the
            // frame rounds these cards a notch softer than everything else.
            <li
              key={nomination.id}
              className="rounded-[19px] border border-brand-line px-3 py-2.5 md:px-3.5 md:py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="flex min-w-0 items-center gap-2 font-bold text-base leading-[22px] md:text-xl md:leading-[27px]">
                  {/* `h`/`w` rather than `size`: the glyph is 20×21, and the dial that
                      hangs below the calendar is what makes it read as a window
                      rather than as a date. */}
                  <CalendarClockIcon
                    className="h-[15.75px] w-[15px] shrink-0 md:h-[21px] md:w-5"
                    aria-hidden="true"
                  />
                  <span className="min-w-0 break-words">{nomination.name}</span>
                </h3>
                <IntakeChip state={state} />
              </div>

              {/* 70% by day and full strength by night: at 70% over `#110B12`
                  the dates stopped being readable, and the frame prints them in
                  «свет» there. A `dark:` class rather than a token — this is one
                  value at two opacities, not two colours from two ramps. */}
              {/* The two facts swap places between the layouts, and the DOM
                  follows the desktop: the date sits right under the name there,
                  dropped to 40% — a quiet caption on the heading — while the
                  phone moves it to the last line and gives it full strength.
                  `order-last` rather than two copies of the markup. */}
              <div className="flex flex-col">
                {held ? (
                  <p className="order-last mt-3 text-foreground text-sm leading-[19px] md:order-none md:mt-0.5 md:text-foreground/40 dark:text-foreground/70 md:dark:text-foreground/70">
                    Дата проведения: {held}
                  </p>
                ) : null}
                <div className="mt-2 text-foreground/70 text-sm leading-[19px] md:text-lg md:leading-[25px] dark:text-foreground">
                  {opens || closes ? (
                    <>
                      <p>Приём заявок</p>
                      <p className="flex flex-wrap gap-x-4 gap-y-0.5 md:gap-x-12">
                        {opens ? <span>с {opens}</span> : null}
                        {closes ? <span>по {closes}</span> : null}
                      </p>
                    </>
                  ) : (
                    <p>Даты приёма заявок пока не назначены</p>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </LandingSection>
  );
}
