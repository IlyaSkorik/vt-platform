import { cn } from "@/shared/lib";

interface LandingSectionProps {
  /** Anchor id, so a deep link can land on the section. */
  id?: string;
  title: string;
  /**
   * Where the heading sits. The frame centres the three full-width sections it
   * puts below the fold — jury, gallery, partners — and keeps the ones inside
   * the right-hand column left-aligned with their content. It is a property of
   * the slot rather than of the section, so the page passes it in.
   */
  align?: "start" | "center";
  /**
   * The margin under the heading, as a utility class.
   *
   * A constant was tried and does not survive contact with the frame: it is 20
   * for every section in the right-hand column, 38 under «Жюри и эксперты» and
   * 26 under «Галерея» and «Партнеры». Deriving it from `align` got two of
   * those three right, which is the worst of both.
   */
  headingGap?: string;
  children: React.ReactNode;
}

/**
 * Shared wrapper for every landing section: the heading, the gap under it, and
 * the scroll margin that keeps an anchored section clear of the sticky header.
 *
 * The heading is «Загаловки» at 32/44 — the one size the frame sets every
 * section title in, stepping down to 24/33 on a phone. It is `font-heading`
 * because the whole public surface is: Noto Serif, headings and body alike.
 *
 * No `subtitle`. Nothing in the frame carries one, and the prop was only ever
 * passed `null` — a section that needs a lead paragraph can render it as its
 * own first child, where it belongs to the content rather than to the chrome.
 */
export function LandingSection({
  id,
  title,
  align = "start",
  headingGap = "mb-1.5 md:mb-5",
  children,
}: LandingSectionProps): React.JSX.Element {
  return (
    <section id={id} className="scroll-mt-24">
      <h2
        className={cn(
          "text-pretty break-words font-heading font-bold text-2xl text-foreground leading-[33px] md:text-[32px] md:leading-[44px]",
          headingGap,
          align === "center" && "text-center",
        )}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
