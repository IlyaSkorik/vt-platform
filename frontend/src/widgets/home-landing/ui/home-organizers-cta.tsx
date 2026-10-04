import { Link } from "react-router";
import { APP_NAME } from "@/shared/config";
import { Button } from "@/shared/ui";

interface HomeOrganizersCtaProps {
  /** Where «Свяжитесь с нами» leads — a `tel:` or `mailto:` the page owns. */
  contactHref: string;
}

/**
 * The closing panel, addressed to the other half of the audience: the people who
 * would *run* a festival rather than enter one.
 *
 * It is the only surface on the landing that is tinted rather than outlined —
 * the design fills it with `--gradient-brand-panel`, a top-to-bottom veil of
 * `светлый акцент` over the page colour. That is what separates it from the
 * white cards above without another outline competing with theirs, and it is why
 * the block reads as a change of subject rather than as one more festival.
 */
export function HomeOrganizersCta({ contactHref }: HomeOrganizersCtaProps): React.JSX.Element {
  return (
    <section
      id="for-organizers"
      // 252px tall in the frame, and 79px in from each edge of a 1440 page —
      // which is where the page container already puts it, to the pixel. So only
      // the height is set here, as a floor rather than a fix: the panel fills it
      // on the current copy and should grow rather than clip if that copy does.
      className="scroll-mt-24 rounded-brand border-2 border-brand-line bg-gradient-brand-panel px-6 py-8 md:min-h-[252px] md:px-10 md:py-9"
    >
      <div className="max-w-5xl space-y-6">
        <h2 className="font-heading font-bold text-2xl text-foreground leading-snug tracking-tight md:text-[1.75rem]">
          Для организаторов
        </h2>
        <p className="max-w-5xl text-pretty font-heading text-foreground/70 text-lg leading-snug dark:text-on-scrim-muted">
          Проводите собственные фестивали? Используйте платформу «{APP_NAME}» для автоматизации
          проведения мероприятий.
        </p>
        {/* 260×46 on the landing's 15px corner, label in Noto Serif Bold 18/25
            — both numbers land on the spacing scale exactly (`w-65`, `h-11.5`),
            so nothing here is pinned in pixels. Full width only on a phone,
            where a 260px button floating in a panel this wide reads as unfinished
            rather than as a measured one. */}
        <Button
          asChild
          size="lg"
          className="h-11.5 w-full rounded-brand px-0 font-heading font-bold text-lg leading-snug hover:bg-brand-line sm:w-65 dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
        >
          <Link to={contactHref}>Свяжитесь с нами</Link>
        </Button>
      </div>
    </section>
  );
}
