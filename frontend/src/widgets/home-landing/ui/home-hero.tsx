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

          Both are anchored top-right rather than centred. The files are 16:9 and
          the band almost never is, so `cover` always has something to cut — and
          centred it cut the two edges that matter: the comet's point at the top
          and its tail at the right, the one thing in the frame that has to
          survive. Pinned to that corner the crop falls on the bottom-left, which
          is wash and fade and loses nothing. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[url('/home-hero-bg.png')] bg-top-right bg-cover bg-no-repeat dark:hidden"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 hidden bg-[url('/home-hero-bg-dark.png')] bg-top-right bg-cover bg-no-repeat dark:block"
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
          address bar would otherwise crop the step cards off the bottom —
          though the rule only applies from `md` up, where the band has room to
          be a composition rather than a stack. */}
      <div className="relative mx-auto flex w-full max-w-336 flex-col gap-14 px-4 pt-12 pb-12 md:min-h-[calc(100svh-3.75rem)] md:gap-0 md:px-8 md:pt-20 md:pb-[65px]">
        <div className="max-w-3xl space-y-6 text-foreground dark:text-on-scrim">
          <div className="space-y-5">
            <h1 className="text-balance font-heading font-bold text-4xl leading-tight tracking-tight sm:text-5xl md:text-display md:leading-[1.43]">
              Взлёт талантов
            </h1>
            {/* An em dash opens it in the design, continuing the title as one
                sentence rather than starting a second one. Kept, because that is
                what makes the title read as a name and this as its definition. */}
            <p className="text-pretty font-heading text-xl leading-snug sm:text-2xl md:text-[2rem]">
              — цифровая платформа для подбора творческих конкурсов и онлайн-регистрации.
            </p>
            <p className="max-w-xl text-pretty font-heading text-foreground/70 text-sm leading-snug dark:text-on-scrim-muted">
              Современный ИТ-сервис для артистов и руководителей, который упрощает путь от выбора
              фестиваля до подтверждения участия.
            </p>
          </div>

          {/* The frame measures the pair and the measurements are kept: 208×43
              and 201×41. 208 is `w-52` on the spacing scale; 43, 201 and 41 are
              not on it at any step, so those three are written out. They look
              like auto-layout leftovers rather than decisions — say the word and
              they round to 208×44 and 200×44, which costs nothing visually and
              puts all four back on the scale.

              The corner is the landing's own 15px, as the export reports. It
              looked wrong for a while only because `cn` was not dropping the
              `rounded-md` the Button variant brings — see the note in
              `shared/lib/cn.ts`. Until that was fixed every radius tried on this
              pair rendered as the same 8px. */}
          <div className="flex flex-wrap items-center gap-4">
            {/* Hover is «тёмный акцент», not the variant's own fade of the
                primary: the frame swaps the fill for `--brand-line` and leaves
                the label white. Every primary button on the landing does the
                same. */}
            <Button
              asChild
              size="lg"
              className="h-[43px] w-52 rounded-brand px-0 font-heading font-bold text-lg leading-snug hover:bg-brand-line dark:bg-brand dark:text-brand-mark dark:hover:bg-brand-line"
            >
              <a href="#upcoming-festivals">Найти фестиваль</a>
            </Button>
            {/* Edge and label are both the frame's «Темный текст» `#211929`
                through `--foreground`, which is what that token resolves to in
                the light theme and what flips it in the dark one: a 1px border
                at full strength, the label at 51%.

                No fill at rest — the `outline` variant's opaque page colour is
                dropped, because in the frame this button is a hairline over the
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
              className="h-[41px] w-[201px] rounded-brand border-foreground bg-transparent px-0 font-heading font-bold text-lg leading-snug text-foreground/51 hover:bg-foreground/6 hover:text-foreground/51 dark:border-on-scrim dark:bg-on-scrim/16 dark:text-on-scrim dark:hover:bg-on-scrim/25 dark:hover:text-on-scrim"
            >
              <Link to={authPath}>Личный кабинет</Link>
            </Button>
          </div>
        </div>

        <HomeSteps className="md:mt-auto md:pt-16" />
      </div>
    </section>
  );
}
