import { ArrowLeft } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import {
  bodyBlocks,
  type FestivalDetail,
  LANDING_BLOCK_TYPES,
  type LandingBlock,
  type RegistrationNominationView,
  usePublicFestival,
  usePublicRegistration,
} from "@/features/festival-landing";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";
import { ContentSection } from "./blocks/content-section";
import { DocumentsSection } from "./blocks/documents-section";
import { FaqSection } from "./blocks/faq-section";
import { GallerySection } from "./blocks/gallery-section";
import { JurySection } from "./blocks/jury-section";
import { PartnersSection } from "./blocks/partners-section";
import { RegistrationBlock } from "./blocks/registration-block";
import { RegulationSection } from "./blocks/regulation-section";
import { ResultsSection } from "./blocks/results-section";
import { VenueSection } from "./blocks/venue-section";
import { LandingCover } from "./landing-cover";
import { LandingFooter } from "./landing-footer";
import { LandingSkeleton } from "./landing-skeleton";
import { LandingError, LandingNotFound } from "./landing-states";
import { LandingSummary } from "./landing-summary";

interface FestivalLandingProps {
  festivalId: string | undefined;
  catalogPath?: string;
}

function BackLink({ to }: { to: string }): React.JSX.Element {
  return (
    <Button asChild variant="ghost" size="sm" leftIcon={<ArrowLeft aria-hidden="true" />}>
      <Link to={to}>К каталогу</Link>
    </Button>
  );
}

/** The first enabled block of a kind, or `null`. One of each is all the builder allows. */
function blockOf(blocks: LandingBlock[], type: string): LandingBlock | null {
  return blocks.find((block) => block.type === type) ?? null;
}

function LandingContent({
  festival,
  applyPath,
  nominations,
}: {
  festival: FestivalDetail;
  applyPath: string;
  nominations: RegistrationNominationView[];
}): React.JSX.Element {
  const blocks = bodyBlocks(festival.landing.blocks);
  // CONTENT is the one kind an organiser can add more than once, so it stays a
  // list and keeps its own `sortOrder`; everything else is at most one block.
  const content = blocks.filter((block) => block.type === LANDING_BLOCK_TYPES.CONTENT);
  const venue = blockOf(blocks, LANDING_BLOCK_TYPES.VENUE);
  const regulation = blockOf(blocks, LANDING_BLOCK_TYPES.REGULATION);
  const documents = blockOf(blocks, LANDING_BLOCK_TYPES.DOCUMENTS);
  const jury = blockOf(blocks, LANDING_BLOCK_TYPES.JURY);
  const gallery = blockOf(blocks, LANDING_BLOCK_TYPES.GALLERY);
  const faq = blockOf(blocks, LANDING_BLOCK_TYPES.FAQ);
  const partners = blockOf(blocks, LANDING_BLOCK_TYPES.PARTNERS);

  return (
    /* `pb-10`: the contacts card is the page's last element and the site
       footer's own border starts immediately under it — two footers with no air
       between them read as one. */
    <div className="pb-10">
      <LandingCover festival={festival} />

      {/* The two columns the frame builds the page's top half from: a fixed
          506px card on the left, the registration column taking the rest. They
          stack below `lg`, where 506 + 773 stops fitting. */}
      <div className="mt-6 grid items-start gap-[41px] md:mt-9 lg:grid-cols-[506px_minmax(0,1fr)] lg:gap-[27px]">
        <LandingSummary festival={festival} applyPath={applyPath} />

        <div className="min-w-0 space-y-6 md:space-y-[30px]">
          <RegistrationBlock nominations={nominations} />
          {/* Positional markers in the builder, fixed positions here: the frame
              puts the regulation under the nominations and the organiser's own
              prose under that, whatever order the blocks carry. The block's
              presence is still what decides whether a section appears at all. */}
          {regulation && festival.regulation ? (
            <RegulationSection regulation={festival.regulation} />
          ) : null}
          {documents ? <DocumentsSection documents={festival.documents} /> : null}
          {content.map((block) => (
            <ContentSection key={block.id} block={block} />
          ))}
          {venue ? <VenueSection id={`block-${venue.id}`} venue={festival.contacts.venue} /> : null}
          {/* Not one of the organiser's blocks: results appear by themselves
              once a protocol is published, because publishing is already the
              deliberate act. Keyed by the competition's uuid rather than by the
              slug in the URL — the Results context answers a slug with nothing. */}
          <ResultsSection festivalId={festival.id} />
        </div>
      </div>

      {/* The rule divides two halves of a wide page — dates and how to enter
          above, people and pictures below. A phone has no two halves to divide:
          there the sections already arrive one after another, and a line across
          the screen reads as a cut rather than as a seam. `hidden` rather than
          a transparent border, so it takes its margin with it.

          Half-strength «тёмный акцент» by day, «светлый база ночная» at full by
          night: the daytime rule is a violet softened against a pale page, and
          the same colour over `#110B12` is a line you cannot find. */}
      <hr className="hidden border-brand-line/50 border-t-2 md:mt-[49px] md:block dark:border-brand-control" />

      {/* Each section carries its own margin rather than the column carrying one
          rhythm: the frame does not space these evenly — 62 under the jury's
          dashes, 84 under the gallery's — and a single `space-y` cannot say
          that. `first:mt-0` keeps the top of the column flush whichever section
          turns out to be first, since every one of them is optional.

          30px under the rule, and on a phone — where there is no rule — the
          whole distance from the prose above it: 24. */}
      <div className="mt-6 md:mt-[30px]">
        {jury ? (
          <div className="first:mt-0">
            <JurySection block={jury} />
          </div>
        ) : null}
        {gallery ? (
          <div className="mt-10 first:mt-0 md:mt-[62px]">
            <GallerySection block={gallery} />
          </div>
        ) : null}
        {faq ? (
          <div className="mt-[52px] first:mt-0 md:mt-[84px]">
            <FaqSection block={faq} />
          </div>
        ) : null}
        {partners ? (
          <div className="mt-[9px] first:mt-0 md:mt-[49px]">
            <PartnersSection block={partners} />
          </div>
        ) : null}
        <div className="mt-16 first:mt-0">
          <LandingFooter contacts={festival.contacts} />
        </div>
      </div>
    </div>
  );
}

/**
 * The public Competition Landing Page.
 *
 * Owns data (a single cached read of the public detail projection) and every UI
 * state: skeleton while loading, a dedicated not-found for a missing or
 * unpublished competition (404), a retryable error otherwise, and the full
 * landing on success.
 *
 * **The page's order is the frame's, not the builder's.** Blocks used to render
 * in the organiser's `sortOrder`, one after another down a single column. The
 * design fixes where each kind lives — the registration column on the right,
 * the jury, gallery, FAQ and partners full-width below the rule — so order is
 * now a property of the page and the builder's ordering no longer reaches the
 * public side. What the organiser still decides is *whether* a block appears:
 * a disabled block is absent from the projection, and an absent block renders
 * nothing here.
 */
export function FestivalLanding({
  festivalId,
  catalogPath = ROUTES.cabinetCompetitions,
}: FestivalLandingProps): React.JSX.Element {
  const { isAuthenticated } = useAuth();
  const query = usePublicFestival(festivalId);
  // Non-blocking: the registration schedule is a secondary read; the page
  // renders without it and the block stays empty until it arrives.
  const registrationQuery = usePublicRegistration(festivalId);
  const applyPath = festivalId
    ? `${ROUTES.cabinetCompetitions}/${festivalId}/apply`
    : ROUTES.cabinetCompetitions;
  const ctaPath = isAuthenticated
    ? applyPath
    : `${ROUTES.login}?next=${encodeURIComponent(applyPath)}`;

  if (!festivalId) {
    return (
      <div className="space-y-6">
        <BackLink to={catalogPath} />
        <LandingNotFound />
      </div>
    );
  }

  if (query.isPending) {
    return <LandingSkeleton />;
  }

  if (query.isError) {
    if (query.error.status === 404) {
      return (
        <div className="space-y-6">
          <BackLink to={catalogPath} />
          <LandingNotFound />
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <BackLink to={catalogPath} />
        <LandingError onRetry={() => void query.refetch()} retrying={query.isFetching} />
      </div>
    );
  }

  return (
    // `font-heading` on the page's root: the public surfaces are set in Noto
    // Serif throughout — headings and body alike — and the application chrome
    // never is, so the opt-in belongs here rather than in each section.
    //
    // No «К каталогу» above the banner. The frame starts the page with the
    // poster, and a back link is the one thing on it the browser already
    // provides. It survives in the error and not-found states below, where
    // there is no page to be on and it is the only way out.
    <div className="font-heading">
      <LandingContent
        festival={query.data}
        applyPath={ctaPath}
        nominations={registrationQuery.data?.nominations ?? []}
      />
    </div>
  );
}
