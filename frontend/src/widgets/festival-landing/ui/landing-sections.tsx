import { bodyBlocks, type FestivalDetail, LANDING_BLOCK_TYPES } from "@/features/festival-landing";
import { ContentSection } from "./blocks/content-section";
import { DocumentsSection } from "./blocks/documents-section";
import { FaqSection } from "./blocks/faq-section";
import { GallerySection } from "./blocks/gallery-section";
import { JurySection } from "./blocks/jury-section";
import { PartnersSection } from "./blocks/partners-section";
import { RegulationSection } from "./blocks/regulation-section";
import { VenueSection } from "./blocks/venue-section";

interface LandingSectionsProps {
  festival: FestivalDetail;
}

/**
 * Render the main-content landing blocks exactly as the organizer configured
 * them: enabled only, in sort order, one section per block type. The VENUE block
 * is a positional marker — it renders the shared Competition Contacts venue at
 * the organizer's chosen place, never a duplicated copy. Unknown/empty blocks
 * render nothing.
 */
export function LandingSections({ festival }: LandingSectionsProps): React.JSX.Element {
  const blocks = bodyBlocks(festival.landing.blocks);
  return (
    <div className="space-y-14">
      {blocks.map((block) => {
        switch (block.type) {
          case LANDING_BLOCK_TYPES.CONTENT:
            return <ContentSection key={block.id} block={block} />;
          case LANDING_BLOCK_TYPES.JURY:
            return <JurySection key={block.id} block={block} />;
          case LANDING_BLOCK_TYPES.PARTNERS:
            return <PartnersSection key={block.id} block={block} />;
          case LANDING_BLOCK_TYPES.GALLERY:
            return <GallerySection key={block.id} block={block} />;
          case LANDING_BLOCK_TYPES.FAQ:
            return <FaqSection key={block.id} block={block} />;
          case LANDING_BLOCK_TYPES.VENUE:
            return (
              <VenueSection
                key={block.id}
                id={`block-${block.id}`}
                venue={festival.contacts.venue}
              />
            );
          case LANDING_BLOCK_TYPES.REGULATION:
            // Positional marker: renders the competition's current regulation at
            // the organizer's chosen spot (nothing if no regulation is set).
            return festival.regulation ? (
              <RegulationSection key={block.id} regulation={festival.regulation} />
            ) : null;
          case LANDING_BLOCK_TYPES.DOCUMENTS:
            // Positional marker: renders the public documents (nothing if none).
            return <DocumentsSection key={block.id} documents={festival.documents} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
