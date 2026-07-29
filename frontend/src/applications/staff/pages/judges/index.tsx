import { useMemo } from "react";
import { useSearchParams } from "react-router";

import {
  DEFAULT_JURY_SECTION,
  findJurySection,
  type JurySectionId,
} from "@/features/jury-protocols";
import { EmptyState, PageContainer } from "@/shared/ui";
import { JuryWorkspaceLayout, ProtocolsSection } from "@/widgets/jury-workspace";

/**
 * The Жюри tab.
 *
 * One implemented section today — Протоколы — because there is no online scoring on the
 * platform: the jury's work here is entering results per nomination and publishing them. The
 * unimplemented sections render an honest placeholder rather than being hidden, so an
 * organizer looking for the roster learns it is coming instead of concluding it is missing.
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
        ) : (
          <EmptyState
            title={`${section.title} — в разработке`}
            description={`${section.description} Пока итоги ведутся в разделе «Протоколы»: результаты по номинациям, публикация и электронные дипломы.`}
          />
        )}
      </JuryWorkspaceLayout>
    </PageContainer>
  );
}
