import { Link } from "react-router";
import { Button } from "@/shared/ui";
import { HomeSteps } from "./home-steps";

interface HomeHeroProps {
  /** Where the secondary action goes — the cabinet when signed in, the login screen otherwise. */
  authPath: string;
}

/**
 * The landing's opening band: the brand artwork, the positioning copy over its
 * pale left half, and the four "how it works" cards resting on its bottom edge.
 *
 * **Why the steps live in here rather than beside it.** In the design they are
 * not a section of their own — they overlap the illustration, and the whole
 * point of them is that the artwork is still visible *through* them. Pulled out
 * into a sibling section they would need the band's height and background
 * duplicated to sit on, and the two would drift apart the first time either
 * changed.
 *
 * The band has no bottom border. The artwork fades into the page colour on its
 * own, and a hairline on top of that fade read as a cut rather than a hand-off.
 */
export function HomeHero({ authPath }: HomeHeroProps): React.JSX.Element {
  return (
    <section className="relative isolate w-full overflow-hidden">
      {/* One artwork per theme. The two are not one picture graded twice: the
          night plate is drawn dark, with its own comet and its own sky, and
          dimming the day plate to stand in for it only ever produced a grey
          version of the wrong image.

          Four plates, not two: the phone gets its own pair, redrawn upright. A
          16:9 landscape plate in a portrait band is cropped to a strip of sky —
          the comet survives, the stage and the performers under it do not, and
          they are what the composition builds to.

          The landscape pair is anchored top-right, the portrait pair top. Neither
          is ever the band's exact ratio, so `cover` always has something to cut,
          and centred it cut the edges that matter. Pinned to those corners the
          crop falls on the bottom, which is wash and fade and loses nothing. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[url('/home-hero-bg-mobile.png')] bg-top bg-cover bg-no-repeat md:bg-[url('/home-hero-bg.png')] md:bg-top-right dark:hidden"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 hidden bg-[url('/home-hero-bg-mobile-dark.png')] bg-top bg-cover bg-no-repeat md:bg-[url('/home-hero-bg-dark.png')] md:bg-top-right dark:block"
      />

      {/* The pale wash the copy is set on — the design's own gesture, a sweep of
          `свет` across the left of the frame that runs out before the stage and
          the silhouettes on the right. Wider on a phone, where the copy spans the
          whole width and has nowhere else to go. */}
      <div
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-full bg-gradient-to-r from-background from-12% to-transparent to-90% md:w-[58%]"
      />

      {/* The hand-off into the page below. A deep fade, not a hairline edge: in
          the design the artwork is already most of the way to the page colour by
          the time the step cards sit on it, so the wash starts near the middle of
          the band and only reaches full `background` at the very bottom. Kept on
          its own layer so the stop positions can move without touching the
          artwork or the scrim above it. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-gradient-to-b from-transparent from-50% via-background/75 via-82% to-background"
      />

      {/* A screenful, less the header: the bar is sticky but still takes its
          60px in the flow, so `100svh` on its own would push the first screen
          that much past the fold. `svh` rather than `vh` because on a phone the
          address bar would otherwise crop the band's bottom edge.

          Same on the phone, against that layout's 38px bar. The rhythm down the
          band is the frame's: 100px of air before the title, 25 to the sentence
          under it, 60 to the buttons. */}
      <div className="relative mx-auto flex min-h-[calc(100svh-38px)] w-full max-w-336 flex-col gap-14 px-7 pt-25 pb-12 md:min-h-[calc(100svh-3.75rem)] md:gap-0 md:px-8 md:pt-20 md:pb-[65px]">
        <div className="max-w-3xl space-y-15 text-foreground md:space-y-6 dark:text-on-scrim">
          <div className="space-y-[25px] md:space-y-5">
            <h1 className="text-balance font-heading font-bold text-[1.75rem] leading-snug tracking-tight sm:text-5xl sm:leading-tight md:text-display md:leading-[1.43]">
              Взлёт талантов
            </h1>
            {/* An em dash opens it in the design, continuing the title as one
                sentence rather than starting a second one. Kept, because that is
                what makes the title read as a name and this as its definition. */}
            <p className="max-w-[303px] text-pretty font-heading text-sm leading-snug sm:max-w-none sm:text-2xl md:text-[2rem]">
              — цифровая платформа для подбора творческих конкурсов и онлайн-регистрации.
            </p>
            {/* Dropped on the phone, as the frame drops it: the artwork's
                performers have to fit under the buttons, a third paragraph
                pushes them off the band, and the sentence above already says
                what the platform is. */}
            <p className="hidden max-w-xl text-pretty font-heading text-foreground/70 text-sm leading-snug md:block dark:text-on-scrim-muted">
              Современный ИТ-сервис для артистов и руководителей, который упрощает путь от выбора
              фестиваля до подтверждения участия.
            </p>
          </div>

          {/* Stacked on a phone by the column, not by wrapping. The two are 186
              and 155 wide with 12 between them — 353 in all, which fits beside
              itself on a 414px screen and not on a 375px one, so `flex-wrap`
              alone made the layout depend on which phone it was. The frame puts
              «Личный кабинет» under «Найти фестиваль» on every one of them.

              The frame measures the pair in both layouts and both are kept:
              186×30 and 155×31 on a 375px phone, 208×43 and 201×41 on the
              desktop. Only 208 lands on the spacing scale (`w-52`); the rest are
              written out.

              The corner is the one thing that is *not* the landing's 15px: the
              phone draws these two at 10, and at 30px tall 15 would have been
              half the height and read as a capsule. The only control on the page
              that does this, which is why it is a class rather than a token.

              Any radius here looked wrong for a while, whatever it was set to,
              because `cn` was not dropping the `rounded-md` the Button variant
              brings — see the note in `shared/lib/cn.ts`. */}
          <div className="flex flex-col items-start gap-3 md:flex-row md:flex-wrap md:items-center md:gap-[18px]">
            {/* Hover is «тёмный акцент», not the variant's own fade of the
                primary: the frame swaps the fill for `--brand-line` and leaves
                the label white. Every primary button on the landing does the
                same. */}
            <Button
              asChild
              size="lg"
              className="h-[30px] w-[186px] rounded-[10px] px-0 font-heading font-bold text-sm leading-snug hover:bg-brand-line md:h-[43px] md:w-52 md:rounded-brand md:text-lg dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
            >
              <a href="#upcoming-festivals">Найти фестиваль</a>
            </Button>
            {/* Edge and label are both the frame's «Темный текст» `#211929`
                through `--foreground`, which is what that token resolves to in
                the light theme and what flips it in the dark one: a 1px border
                at full strength, the label at 51%.

                The phone keeps one thing constant across its two themes: the
                edge is «тёмный акцент» in both, where the desktop swaps it for
                the page's own ink. What changes with the theme there is the fill
                — a solid plate of `свет` by day (`#F9F9F9`, which is what
                `--background` resolves to), the same `свет` at 9% at night. The
                copy sits on the artwork itself in that layout rather than on a
                pale wash, so an unfilled outline disappeared into the sky.

                On the desktop there is no fill at rest — the `outline` variant's
                opaque page colour is dropped, because in the frame this button
                is a hairline over the
                illustration and what shows through it is the artwork. Hover
                tints it 6% of the same ink and changes nothing else: the label
                keeps its 51% rather than darkening, which is what makes the
                press read as the surface responding rather than the text.

                The night frame inverts all three. Over a dark sky a hairline
                disappears, so there it is `свет` at full strength around a 16%
                glass fill, with the label at full `свет` rather than let down —
                the artwork behind is dark enough to carry it. */}
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-[31px] w-[155px] rounded-[10px] border-brand-line bg-background px-0 font-heading font-bold text-sm leading-snug text-foreground/51 hover:bg-foreground/6 hover:text-foreground/51 md:h-[41px] md:w-[201px] md:rounded-brand md:border-foreground md:bg-transparent md:text-lg dark:bg-on-scrim/9 dark:text-on-scrim dark:hover:bg-on-scrim/25 dark:hover:text-on-scrim md:dark:border-on-scrim md:dark:bg-on-scrim/16"
            >
              <Link to={authPath}>Личный кабинет</Link>
            </Button>
          </div>
        </div>

        {/* Not on the phone. Stacked one above another the four cards become a
            list as long as the page they introduce, and they cover the artwork
            they were drawn to float on. */}
        <HomeSteps className="hidden md:mt-auto md:grid md:pt-16" />
      </div>
    </section>
  );
}
