import { Link } from "react-router";
import { CookieSettingsButton } from "@/features/cookie-consent";
import { APP_NAME, ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib/cn";

interface SiteFooterProps {
  /**
   * `brand` is the public site's closing band — a solid `светлый акцент` plate,
   * the bookend to the header. `default` is the strip of fine print the three
   * workspace shells end on, which the Figma file does not draw and which should
   * not suddenly become a brand gesture at the bottom of a working screen.
   */
  variant?: "default" | "brand";
  /** Layout override from the shell, e.g. the public band's measured height. */
  className?: string;
}

export function SiteFooter({
  variant = "default",
  className,
}: SiteFooterProps = {}): React.JSX.Element {
  const entrepreneurName = "Скорик Илья Андреевич";
  const legalStatus = "Плательщик налога на профессиональный доход";
  const unp = "УНП: AE9395951";

  // The band is drawn empty in the frame, so the type on it is not designed and
  // these are chosen rather than transcribed. They are the page's own ink, not
  // the white the header uses: the plate here is `светлый акцент` at just over
  // half strength, paler than the header's solid band, and white on it would set
  // well under 2:1. Three columns of legal text is the one place on the site
  // where that is not a trade worth making. `--foreground` clears AA on this
  // plate in both themes, because it flips with the surface.
  const brand = variant === "brand";
  // `--brand-band` is the plate: `светлый акцент` at 53% by day, a deep violet
  // at half strength at night — one token because it is the same gesture in
  // two lights, and neither value is a tint of the other. Ruled off with
  // `тёмный акцент` in both, and
  // set in the display face — the public side is Noto Serif throughout, and a
  // footer that drops into Inter reads as a different site's. The workspace
  // shells keep the product face, which is what the rest of their screen is in.
  const plate = brand
    ? "flex flex-col border-brand-line border-t-2 bg-brand-band font-heading"
    : "border-border/70 border-t bg-background/80";
  const bodyTone = brand ? "text-foreground/75" : "text-muted-foreground";
  // Set as a heading, not as a slightly heavier line of body copy: Noto Serif
  // Bold 18/25, the same weight the landing gives the step cards' titles. At
  // `font-medium` on a 14px grid the three column names were barely louder than
  // the text under them and the footer read as one undifferentiated block.
  const headingTone = brand
    ? "font-bold text-foreground text-lg leading-snug"
    : "font-medium text-foreground";
  const linkTone = "hover:text-foreground hover:underline";
  const ruleTone = brand ? "border-brand-line" : "border-border/70";
  // `mt-auto` rather than a measured gap: the band is 250px tall and the columns
  // do not fill it, so the copyright drops to the floor of whatever is left and
  // the slack sits above it instead of pooling under it. The rule keeps its
  // hairline — only the colour is the header rule's.
  const tailOffset = brand ? "mt-auto" : "mt-6";

  return (
    <footer className={cn("px-4 pt-8 pb-4 md:px-8", plate, className)}>
      {/* Three columns only from xl. Beside the workspace sidebar a tablet gives
          this footer ~416px, and splitting that three ways left ~123px per column
          — narrower than «профессиональный» or «Пользовательское», which spilled
          into the neighbouring column. `wrap-anywhere` is the last resort: it,
          unlike `break-words`, also lowers the intrinsic minimum the shrink-to-fit
          link boxes are measured by. */}
      <div
        className={cn(
          "mx-auto grid w-full max-w-7xl gap-6 wrap-anywhere text-sm md:grid-cols-2 xl:grid-cols-3",
          bodyTone,
        )}
      >
        <div className="space-y-2">
          <p className={headingTone}>{APP_NAME}</p>
          <p>Платформа фестивалей и онлайн-подачи заявок.</p>
        </div>

        <div className="space-y-2">
          <p className={headingTone}>Документы</p>
          <div className="flex flex-col items-start gap-1">
            {/* First, because it is the one document that is a contract: the account
                exists because the person accepted it (LEGAL-003 §3.2). */}
            <Link to={ROUTES.termsOfService} className={linkTone}>
              Пользовательское соглашение
            </Link>
            <Link to={ROUTES.privacyPolicy} className={linkTone}>
              Политика обработки персональных данных
            </Link>
            <Link to={ROUTES.cookiesPolicy} className={linkTone}>
              Политика использования файлов cookie
            </Link>
            {/* The way back to the cookie decision. It belongs here, in the one place
                present on every page, because that is where the policy tells visitors
                to look for it (LEGAL-002 §2.4, §7.1). */}
            <CookieSettingsButton className={cn("cursor-pointer", linkTone)} />
          </div>
        </div>

        <div className="space-y-2">
          <p className={headingTone}>Реквизиты</p>
          <p>{entrepreneurName}</p>
          <p>{legalStatus}</p>
          <p>{unp}</p>
        </div>
      </div>
      <div
        className={cn(
          "mx-auto w-full max-w-7xl border-t pt-4 text-center text-xs",
          tailOffset,
          ruleTone,
          bodyTone,
        )}
      >
        © {new Date().getFullYear()} {APP_NAME}
      </div>
    </footer>
  );
}
