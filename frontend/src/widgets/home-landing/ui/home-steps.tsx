import { cn } from "@/shared/lib/cn";

/** One stop on the path from finding a festival to holding the diploma. */
interface Step {
  title: string;
  description: string;
}

/**
 * The four steps, in the order a participant actually meets them. Declared as
 * data rather than four hand-written cards so the row cannot drift out of
 * alignment one card at a time.
 */
const STEPS: readonly Step[] = [
  {
    title: "Найти фестиваль",
    description: "Выберите фестиваль с помощью удобной фильтрации.",
  },
  {
    title: "Подать заявку",
    description: "Зарегистрируйтесь и отправьте заявку на выбранное мероприятие онлайн.",
  },
  {
    title: "Просмотр результатов",
    description: "Следите за публикацией итогов жанров и протоколов.",
  },
  {
    title: "Скачать диплом",
    description: "Получите дипломы и сертификаты после публикации результатов.",
  },
];

interface HomeStepsProps {
  className?: string;
}

/**
 * The "how it works" row that rests on the bottom of the hero artwork.
 *
 * The cards are **barely filled on purpose** — `свет` at 23% by day and 5% at
 * night, a wash rather than a surface. They are meant to read as glass laid on
 * the illustration, so the stage lights and the silhouettes stay visible through
 * them; an opaque card here would cover exactly the part of the artwork the
 * composition builds to. There is deliberately no `backdrop-blur`: the frame
 * does not frost what shows through, and at 5% the blur was most of what the
 * card was doing.
 * What makes them legible instead is the pair the design uses everywhere: a
 * `тёмный акцент` outline, and `светяшка светлая` — an even halo with no offset,
 * which lifts the card off a busy background without the directional shadow that
 * would read as a cut-out pasted on top.
 *
 * Not a list of links: none of the four is a destination. They describe the
 * flow, and the buttons above and below are what actually enter it.
 */
export function HomeSteps({ className }: HomeStepsProps): React.JSX.Element {
  return (
    <ul
      className={cn(
        // The frame's own measurements, but only once there is room for the row
        // it measured: four 250px cards, 69px apart, centred in the container —
        // 1207px of the 1280 it has. Below `xl` the numbers are dropped and the
        // cards go back to filling their column, because a 250px card in a
        // two-up grid on a tablet is just a card with a hole beside it.
        "grid justify-center gap-6 sm:grid-cols-2 xl:grid-cols-[repeat(4,250px)] xl:gap-[69px]",
        className,
      )}
    >
      {STEPS.map((step) => (
        <li
          key={step.title}
          // `min-h` and not `h`: 123px is what the frame's content comes to, and
          // it is exactly what this renders at — but a longer description should
          // push the card taller rather than spill out the bottom of it.
          className="rounded-brand border-[3px] border-brand-line bg-brand-glass px-4 py-5 shadow-glow-soft xl:min-h-[123px]"
        >
          {/* Noto Serif Bold 18/25 above Regular 12/16, from the frame.
              The heading runs the full inner width, cancelling the card's own
              16px inset — «Просмотр результатов» needs about 222px of the 212
              the padding leaves, and would break onto a second line. It does not
              in the frame only because a Figma text layer is not clipped by the
              rectangle behind it: that title is measured 8px wider than the card
              it sits on. Centred text, so giving it the extra room changes
              nothing visually until a title actually needs it.

              The caption's colour is the frame's «полупрозрачный текст» —
              `#211929` at 40%, which is `--foreground` at 40% to the byte in the
              light theme and flips with the surface in the dark one, where a 40%
              near-black would be a 40% hole. */}
          <p className="-mx-4 text-center font-heading font-bold text-foreground text-lg leading-snug dark:text-on-scrim">
            {step.title}
          </p>
          <p className="mt-2 font-heading text-foreground/40 text-xs leading-4 dark:text-on-scrim-muted">
            {step.description}
          </p>
        </li>
      ))}
    </ul>
  );
}
