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
      className="scroll-mt-24 min-h-[228px] rounded-brand border-2 border-brand-line bg-gradient-brand-panel px-5 pt-5 pb-6 md:min-h-[252px] md:px-10 md:py-9"
    >
      {/* Centred on the phone. The panel is nearly the width of the screen
          there, and the three things in it — name, sentence, button — read as a
          block rather than as the left column of something wider. */}
      {/* Margins per child rather than one `space-y`: the frame does not
          space these three evenly on the phone — 20px from the name to the
          sentence, 28 from the sentence to the button — and `space-y-*` would
          win over a child's own `mt-*` on specificity if it were kept. */}
      <div className="max-w-5xl text-center md:text-left">
        <h2 className="font-heading font-bold text-base text-foreground leading-snug tracking-tight md:text-[1.75rem]">
          Для организаторов
        </h2>
        <p className="mx-auto mt-5 max-w-[273px] text-pretty font-heading text-foreground/70 text-sm leading-snug md:mx-0 md:mt-6 md:max-w-5xl md:text-lg dark:text-on-scrim-muted">
          Проводите собственные фестивали? Используйте платформу «{APP_NAME}» для автоматизации
          проведения мероприятий.
        </p>
        {/* 197×37 on the phone and 260×46 on the desktop, label in Noto Serif
            Bold 14/19 and 18/25
            — both numbers land on the spacing scale exactly (`w-65`, `h-11.5`),
            so nothing here is pinned in pixels. Full width only on a phone,
            where a 260px button floating in a panel this wide reads as unfinished
            rather than as a measured one. */}
        <Button
          asChild
          size="lg"
          className="mx-auto mt-7 h-[37px] w-[197px] rounded-brand px-0 font-heading font-bold text-sm leading-snug hover:bg-brand-line md:mx-0 md:mt-6 md:h-11.5 md:w-65 md:text-lg dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
        >
          <Link to={contactHref}>Свяжитесь с нами</Link>
        </Button>
      </div>
    </section>
  );
}
