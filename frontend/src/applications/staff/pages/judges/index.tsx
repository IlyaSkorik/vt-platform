import { useMemo } from "react";
import { useSearchParams } from "react-router";

import {
  DEFAULT_JURY_SECTION,
  findJurySection,
  type JurySectionId,
} from "@/features/jury-protocols";
import { EmptyState, PageContainer } from "@/shared/ui";
import {
  JuryAssignmentsSection,
  JuryMembersSection,
  JuryWorkspaceLayout,
  LiveScoringSection,
  ProtocolsSection,
  TallySection,
} from "@/widgets/jury-workspace";

/**
 * The Жюри tab.
 *
 * Протоколы is the section every festival uses and stays the default: whether or not the
 * jury scores on the platform, the results end up in a protocol that gets published.
 *
 * The other four exist for festivals that judge online — the panel, its assignments, the
 * host's running order and the tally. They are listed for everybody rather than hidden:
 * an organizer who has just switched the mode on needs somewhere to find what they
 * switched on, and each one explains itself when the festival is on protocols instead.
 */
export function StaffJudgesPage(): React.JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeSection = (searchParams.get("section") ?? DEFAULT_JURY_SECTION) as JurySectionId;
  const section = useMemo(() => findJurySection(activeSection), [activeSection]);

  const handleSectionChange = (nextSection: JurySectionId): void => {
    setSearchParams({ section: nextSection }, { replace: true });
  };

  return (
    <PageContainer size="full" className="gap-0">
      <JuryWorkspaceLayout
        activeSection={section.id}
        sectionTitle={section.title}
        sectionDescription={section.description}
        onSectionChange={handleSectionChange}
      >
        {section.id === "protocols" ? (
          <ProtocolsSection />
        ) : section.id === "members" ? (
          <JuryMembersSection />
        ) : section.id === "assignments" ? (
          <JuryAssignmentsSection />
        ) : section.id === "live" ? (
          <LiveScoringSection />
        ) : section.id === "tally" ? (
          <TallySection />
        ) : (
          <EmptyState title={`${section.title} — в разработке`} description={section.description} />
        )}
      </JuryWorkspaceLayout>
    </PageContainer>
  );
}
